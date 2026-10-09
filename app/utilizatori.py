"""Utilizatorii aplicației și rolul lor (tabela `utilizatori`, migrarea 040).

De ce: AD-ul verifică doar parola, iar rolul (admin / analist) se dă în aplicație, din pagina
„Utilizatori”, ca în SCC (decizia din 09.10.2026). E singurul loc din server care scrie în bază.

  - `la_logare`: după o parolă bună în AD contul apare în tabelă fără rol (blocat), ca adminul să-l
    vadă în pagină; contul din `MCC_ADMIN_INITIAL` primește admin, dar doar la creare, deci nu
    poate fi folosit ca să-și recapete rolul după ce un alt admin i l-a luat;
  - `modifica`: rolul și starea, cu două opriri pe care SCC nu le are: nimeni nu-și retrage singur
    drepturile de admin și nu se poate retrage ultimul admin activ (aplicația ar rămâne fără cine
    să dea roluri, iar reparația ar cere SQL de mână pe server).

Erorile lui `modifica` sunt coduri (`Respins.cod`), traduse în interfață (`ut.eroare.*`).
"""

import psycopg2
import psycopg2.extras

ROLURI = ("admin", "analist")
COLOANE = "utilizator, nume, rol, activ, creat, ultima_logare, modificat, modificat_de"
MOMENTE = ("creat", "ultima_logare", "modificat")


class Respins(Exception):
    """Cerere refuzată (400), cu codul erorii pentru interfață."""

    def __init__(self, cod):
        super().__init__(cod)
        self.cod = cod


class Lipsa(Exception):
    """Utilizatorul nu există în tabelă (404)."""


def _iso(rand):
    """Momentele în ISO 8601 (cu „T”): str(datetime) pune un spațiu, pe care Safari nu-l citește."""
    rand = dict(rand)
    for k in MOMENTE:
        if rand.get(k) is not None:
            rand[k] = rand[k].isoformat()
    return rand


def rol_efectiv(rand):
    """Rolul cu care contul folosește aplicația: niciunul dacă e dezactivat."""
    return rand["rol"] if rand["activ"] else None


class Utilizatori:
    def __init__(self, dsn, admin_initial=""):
        self.dsn = dsn
        self.admin_initial = (admin_initial or "").strip().lower()

    def _conecteaza(self):
        return psycopg2.connect(self.dsn)

    def disponibil(self):
        conn = self._conecteaza()
        try:
            with conn, conn.cursor() as cur:
                cur.execute("SELECT to_regclass('public.utilizatori') IS NOT NULL")
                return cur.fetchone()[0]
        finally:
            conn.close()

    def la_logare(self, utilizator, nume):
        """Rolul cu care intră contul, după ce AD-ul i-a verificat parola; None = fără acces.

        Numele din AD se actualizează la fiecare logare; rolul nu se atinge decât la creare."""
        rol_initial = "admin" if self.admin_initial and utilizator == self.admin_initial else None
        conn = self._conecteaza()
        try:
            with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO utilizatori (utilizator, nume, rol, ultima_logare)
                       VALUES (%s, %s, %s, now())
                       ON CONFLICT (utilizator) DO UPDATE
                         SET nume = EXCLUDED.nume, ultima_logare = now()
                       RETURNING rol, activ""",
                    (utilizator, (nume or "").strip() or utilizator, rol_initial))
                return rol_efectiv(cur.fetchone())
        finally:
            conn.close()

    def lista(self):
        """Toate conturile; cele care așteaptă un rol primele, apoi după ultima logare."""
        if not self.disponibil():
            return {"disponibil": False}
        conn = self._conecteaza()
        try:
            with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(f"""SELECT {COLOANE} FROM utilizatori
                                ORDER BY (rol IS NULL AND activ) DESC, ultima_logare DESC NULLS LAST,
                                         utilizator""")
                return {"disponibil": True, "utilizatori": [_iso(r) for r in cur.fetchall()]}
        finally:
            conn.close()

    def modifica(self, utilizator, corp, de_catre):
        """Schimbă `rol` și/sau `activ`. Întoarce (rândul nou, rândul vechi).

        `rol: null` lasă contul fără acces (ca la prima logare); `activ: false` îl blochează și
        păstrează rolul, pentru o reactivare. Aruncă Respins (400) sau Lipsa (404)."""
        if not isinstance(utilizator, str) or not utilizator or len(utilizator) > 64:
            raise Respins("utilizator_invalid")
        campuri = {}
        if "rol" in corp:
            if corp["rol"] is not None and corp["rol"] not in ROLURI:
                raise Respins("rol_invalid")
            campuri["rol"] = corp["rol"]
        if "activ" in corp:
            if not isinstance(corp["activ"], bool):
                raise Respins("activ_invalid")
            campuri["activ"] = corp["activ"]
        if not campuri:
            raise Respins("nimic_de_modificat")
        conn = self._conecteaza()
        try:
            with conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Adminii activi, blocați până la COMMIT: două retrageri simultane, fiecare văzând
                # „mai rămâne unul”, ar lăsa altfel aplicația fără niciun admin.
                cur.execute("SELECT utilizator FROM utilizatori WHERE rol = 'admin' AND activ "
                            "ORDER BY utilizator FOR UPDATE")
                admini = {r["utilizator"] for r in cur.fetchall()}
                cur.execute(f"SELECT {COLOANE} FROM utilizatori WHERE utilizator = %s FOR UPDATE",
                            (utilizator,))
                vechi = cur.fetchone()
                if vechi is None:
                    raise Lipsa(utilizator)
                nou = {**vechi, **campuri}
                if utilizator in admini and rol_efectiv(nou) != "admin":
                    if utilizator == de_catre:
                        raise Respins("propriul_cont")
                    if len(admini) == 1:
                        raise Respins("ultimul_admin")
                cur.execute(f"""UPDATE utilizatori
                                   SET rol = %s, activ = %s, modificat = now(), modificat_de = %s
                                 WHERE utilizator = %s
                             RETURNING {COLOANE}""",
                            (nou["rol"], nou["activ"], de_catre, utilizator))
                return _iso(cur.fetchone()), _iso(vechi)
        finally:
            conn.close()
