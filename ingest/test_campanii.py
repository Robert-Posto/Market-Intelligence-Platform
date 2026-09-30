"""Teste pentru colectorul de campanii (migrarea 019), fără rețea.

Orice conexiune de rețea deschisă din Python pică testul (socket-ul e
înlocuit), iar `transport.adu` e simulat unde colectorul ar cere ceva.
Paginile reale sunt citite din `bronze/` (dacă lipsesc, testul se sare).
Testul de scriere în bază rulează doar dacă migrarea 019 e aplicată, într-o
tranzacție anulată la final: nu lasă nimic în bază.

    python ingest/test_campanii.py
"""

import datetime
import os
import re
import socket
import sys
import tempfile
import unittest
from unittest import mock

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path[:0] = [RADACINA, AICI]


def _fara_retea(*a, **k):
    raise AssertionError("cerere de rețea într-un test offline")


socket.socket.connect = _fara_retea
socket.create_connection = _fara_retea

import campanii as C                    # noqa: E402
import campanii_config as K             # noqa: E402
import campanii_extractie as E          # noqa: E402
import flux                             # noqa: E402
import normalizeaza_campanii as NC      # noqa: E402
import transport                        # noqa: E402

AZI = datetime.date(2026, 9, 29)


def _bronze(test, url):
    cale = flux.cale_bronze(url)
    if not os.path.exists(cale):
        test.skipTest(f"lipsește din Bronze: {os.path.basename(cale)}")
    with open(cale, "rb") as f:
        return f.read(), cale


def _doc(test, url, slug):
    octeti, cale = _bronze(test, url)
    cfg = K.CONFIG[slug]
    return E.document(octeti, url, cale=cale, nume_banca=cfg["nume"], nume_grup=cfg.get("grup", ()))


class TestPerioadaPeBronze(unittest.TestCase):
    """Pagini și regulamente reale, aduse de popularea de prețuri."""

    def test_garanti_pagina_html(self):
        d = _doc(self, "https://www.garantibbva.ro/campanii-incheiate/campanie-depozite-pensionari", "garanti")
        p = d["perioada"]
        self.assertEqual((p["start"], p["sfarsit"]), (datetime.date(2022, 9, 6), datetime.date(2022, 12, 31)))
        self.assertIn("6 Septembrie 2022", p["citat"])
        self.assertIn("0,30%", d["beneficiu"])

    def test_tbi_regulament_cu_ora(self):
        d = _doc(self, "https://tbibank.ro/wp-content/uploads/2026/07/Regulament-August-Garantat-5000-lei-auto.pdf", "tbi")
        p = d["perioada"]
        self.assertEqual((p["start"], p["sfarsit"]), (datetime.date(2026, 8, 1), datetime.date(2026, 8, 31)))
        self.assertEqual(d["organizator"][0], "banca")
        self.assertIn("5.000 lei", d["beneficiu"])

    def test_raiffeisen_anul_de_la_capatul_al_doilea(self):
        d = _doc(self, "https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/regulamente/2026/"
                       "septembrie/20260921-regulamentul-campaniei-promotionale-deschide-pachetul-de-cont-"
                       "curent-premium-si-poti-castiga-un-premiu-in-valoare-de-5000-lei.sv.pdf", "raiffeisen")
        p = d["perioada"]
        self.assertEqual((p["start"], p["sfarsit"]), (datetime.date(2026, 9, 21), datetime.date(2026, 12, 31)))
        self.assertFalse(p["an_dedus"])

    def test_bcr_ora_am_si_numere_de_articol(self):
        # „8.1 si 8.2 de mai sus" nu e interval; „15.09.2026 ora 00:00 AM – 31.12.2026" e
        d = _doc(self, "https://cdn.erstegroup.com/content/dam/ro/bcr/www_bcr_ro/Campanii/2026/pf-regulamente/"
                       "Regulament-campanie-Depozitul-Promo-pe-5-luni-in-Lei-si-EUR_Sume-Noi-Toamna.pdf", "bcr")
        p = d["perioada"]
        self.assertEqual((p["start"], p["sfarsit"]), (datetime.date(2026, 9, 15), datetime.date(2026, 12, 31)))

    def test_brd_organizatorul_nu_e_schema_din_numele_campaniei(self):
        d = _doc(self, "https://www.brd.ro/_files/pdf/Castiga-cu-cardul-tau-Mastercard-Business-de-la-BRD-"
                       "regulament-aprilie-2024.pdf", "brd")
        self.assertEqual(d["organizator"][0], "banca")
        self.assertFalse(d["act_aditional"], "clauza „se va încheia un act adițional” nu e un act existent")

    def test_brd_pdf_scanat_perioada_din_nume(self):
        url = "https://www.brd.ro/_files/pdf/Regulament%20autentificat%20Youth%2007.09-30.11.2026.pdf"
        d = _doc(self, url, "brd")
        self.assertTrue(d["fara_text"])
        p = E.perioada_din_url(url)
        self.assertEqual((p["start"], p["sfarsit"]), (datetime.date(2026, 9, 7), datetime.date(2026, 11, 30)))

    def test_raiffeisen_act_aditional_existent(self):
        d = _doc(self, "https://www.raiffeisen.ro/content/dam/rbi/retail/eu/ro/documents/regulamente/2026/iulie/"
                       "20260701-regulament-3-6-9-rate-fara-dobanda-oriunde-in-lume-din-smart-mobile.sv.pdf",
                 "raiffeisen")
        self.assertTrue(d["act_aditional"])

    def test_salt_etichetele_din_indexul_de_regulamente(self):
        octeti, _ = _bronze(self, "https://salt.bank/documente/campanii-si-promotii")
        ctx = C.Context("salt", K.CONFIG["salt"])
        cand, _ = C.candidati_din_pagina(octeti, "https://salt.bank/documente/campanii-si-promotii", ctx, "t")
        self.assertGreater(len(cand), 20)
        cu_perioada = [c for c in cand if E.perioada(c["eticheta"] or "", eticheta=True)]
        self.assertGreater(len(cu_perioada), 10)


class TestPerioadaSintetic(unittest.TestCase):
    def per(self, text, **kw):
        p = E.perioada(text, **kw)
        return (p["start"], p["sfarsit"]) if p else None

    def test_forme(self):
        d = datetime.date
        self.assertEqual(self.per("Campania se desfasoara in perioada 01.07.2026 - 30.09.2026."),
                         (d(2026, 7, 1), d(2026, 9, 30)))
        self.assertEqual(self.per("Oferta valabila intre 1 si 31 august 2026."), (d(2026, 8, 1), d(2026, 8, 31)))
        self.assertEqual(self.per("Campania: 1 - 31 august 2026"), (d(2026, 8, 1), d(2026, 8, 31)))
        self.assertEqual(self.per("in perioada 01.07 - 30.09.2026"), (d(2026, 7, 1), d(2026, 9, 30)))
        self.assertEqual(self.per("Promoția e valabilă în perioada 15 decembrie – 15 ianuarie 2027"),
                         (d(2026, 12, 15), d(2027, 1, 15)))
        self.assertEqual(self.per("Oferta valabila pana la 31.05.2018."), (None, d(2018, 5, 31)))

    def test_fara_ancora_nu_se_ghiceste_ca_sigura(self):
        p = E.perioada("contract nr. 2177 din 05.01.2017 - 30.03.2018")
        self.assertFalse(p["ancorata"])

    def test_numere_de_articol_nu_sunt_date(self):
        self.assertIsNone(E.perioada("conform art. 8.1 si 8.2 de mai sus"))

    def test_exemplul_de_calcul_nu_e_termen(self):
        self.assertIsNone(E.perioada("Oferta ING. Exemplul este valabil pana la 31.07.2026."))

    def test_an_lipsa_din_url(self):
        p = E.perioada_din_url("https://credex.ro/wp-content/uploads/2026/08/Regulament-12-rate-09.07-30.09.pdf")
        self.assertEqual(p["sfarsit"], datetime.date(2026, 9, 30))
        self.assertTrue(p["an_dedus"])

    def test_o_singura_zi_in_eticheta(self):
        p = E.perioada("Campanie Cafeaua BOILER - 27 septembrie 2025", eticheta=True)
        self.assertTrue(p["o_singura_zi"])

    def test_act_aditional(self):
        self.assertFalse(E.are_act_aditional("In cazul in care Organizatorul va decide modificarea duratei, "
                                             "se va incheia un act aditional"))
        self.assertTrue(E.are_act_aditional("ACTUL ADITIONAL NR. 1 la Regulamentul campaniei"))
        self.assertTrue(E.are_act_aditional("Se prelungeste durata Programului pana la 31 Octombrie 2026"))


def _docs(**kw):
    baza = {"verdict": "OK", "format": "pdf", "fara_text": False, "perioada": None, "titlu": "Campania X",
            "beneficiu": None, "organizator": None, "act_aditional": False, "nedeterminat": None,
            "data_maxima": None}
    baza.update(kw)
    return baza


class TestClasificareStricta(unittest.TestCase):
    U = "https://bank.ro/regulament-x.pdf"

    def camp(self, **kw):
        membri = [{"url": self.U, "rol_document": "regulament", "eticheta": kw.pop("eticheta", None),
                   "url_hub": kw.pop("url_hub", None)}]
        return NC.campanie(self.U, membri, {self.U: _docs(**kw)}, AZI, "hub")

    def per(self, st, sf, **kw):
        return {"start": st, "sfarsit": sf, "citat": "c", "ancorata": True, "an_dedus": False,
                "o_singura_zi": False, **kw}

    def test_activa(self):
        r, _ = self.camp(perioada=self.per(datetime.date(2026, 9, 1), datetime.date(2026, 12, 31)))
        self.assertEqual((r["tip_oferta"], r["stare"], r["sursa_ferestrei"]), ("campanie", "activa", "document"))

    def test_incheiata(self):
        r, _ = self.camp(perioada=self.per(datetime.date(2024, 4, 3), datetime.date(2024, 5, 31)))
        self.assertEqual(r["stare"], "incheiata")

    def test_fara_perioada_de_verificat(self):
        r, _ = self.camp()
        self.assertEqual((r["tip_oferta"], r["stare"]), (None, "de_verificat"))
        self.assertIn("fără perioadă", r["motiv_verificare"])

    def test_act_aditional_de_verificat(self):
        r, _ = self.camp(perioada=self.per(datetime.date(2026, 9, 1), datetime.date(2026, 12, 31)),
                         act_aditional=True)
        self.assertEqual(r["stare"], "de_verificat")

    def test_an_dedus_de_verificat(self):
        r, _ = self.camp(perioada=self.per(datetime.date(2026, 7, 9), datetime.date(2026, 9, 30), an_dedus=True))
        self.assertEqual(r["stare"], "de_verificat")

    def test_program_fara_termen(self):
        r, _ = self.camp(titlu="Programul de beneficii", nedeterminat="perioada nedeterminat")
        self.assertEqual((r["tip_oferta"], r["stare"]), ("program", "activa"))

    def test_treapta_b(self):
        r, _ = self.camp(data_maxima=datetime.date(2023, 5, 1))
        self.assertEqual((r["tip_oferta"], r["stare"]), (None, "incheiata"))

    def test_doar_eticheta_documentul_neadus(self):
        r, _ = self.camp(verdict="ROBOTS", eticheta="Cursa Plăților – 15-17 Octombrie 2025")
        self.assertEqual((r["sursa_ferestrei"], r["stare"]), ("eticheta_link", "de_verificat"))

    def test_organizator_si_hub_in_legaturi(self):
        r, leg = self.camp(organizator=("schema_card", "Organizatorul este Mastercard Europe SA"),
                           url_hub="https://bank.ro/campanii")
        self.assertEqual(r["organizator"], "schema_card")
        self.assertEqual({x["rol_document"] for x in leg}, {"regulament", "hub"})

    def test_newsroom_capcane(self):
        self.assertFalse(NC.e_campanie("Premieră în bankingul românesc")[0])
        self.assertFalse(NC.e_campanie("Câștigătorii au fost anunțați")[0])
        self.assertFalse(NC.e_campanie("O nouă campanie de phishing vizează clienții")[0])
        self.assertTrue(NC.e_campanie("Câștigă 500 lei cu cardul")[0])


def _rez(verdict, octeti=b"", url=None, nota=None):
    return transport.Rezultat(verdict, octeti if verdict == "OK" else None, url, "http", nota)


class TestColectorCuTransportSimulat(unittest.TestCase):
    """Toate cererile trec prin `transport.adu`; aici e simulat."""

    CFG = {"baza": "https://bank.ro/", "huburi": ["https://bank.ro/campanii"], "sitemap": False,
           "arhive": ["https://bank.ro/campanii-incheiate"], "nume": [r"banca x"]}
    HUB = ('<html><body><main>'
           '<a href="/campanii/card-cashback">Cashback 10% cu cardul</a>'
           '<a href="/campanii-incheiate/vechi">Campanie veche</a>'
           '<a href="/castigatori-2026">Lista câștigătorilor</a>'
           '<a href="/referral?promotion=ABC">Recomandă</a>'
           '<a href="https://online.bank.ro/aplica">Aplică</a>'
           '<a href="/en/campaigns/cashback">EN</a>'
           '<a href="/campanii-incheiate">Arhivă</a>'
           '</main></body></html>').encode()
    LANDING = ('<html><head><meta property="og:title" content="Cashback 10% cu cardul">'
               '<meta name="description" content="Primești 10% cashback, până la 200 lei."></head>'
               '<body><main><h1>Cashback 10%</h1><p>Campania se desfășoară în perioada 01.09.2026 - '
               '31.12.2026.</p><a href="/documente/regulament-cashback.pdf">Regulamentul campaniei</a>'
               '</main></body></html>').encode()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cerute = []

        def adu(url, banca, stare):
            self.cerute.append(url)
            if url.rstrip("/") == "https://bank.ro":
                return _rez("OK", b"<html><body><main>Bine ai venit</main></body></html>", url)
            if url == "https://bank.ro/campanii":
                return _rez("OK", self.HUB, url)
            if url == "https://bank.ro/campanii/card-cashback":
                return _rez("OK", self.LANDING, url)
            if url.endswith("regulament-cashback.pdf"):
                return _rez("ROBOTS", url=url, nota="interzis de robots.txt")
            return _rez("DISPARUT", url=url, nota="HTTP 404")

        for tinta, valoare in ((transport, "adu"),):
            p = mock.patch.object(tinta, valoare, side_effect=adu)
            p.start()
            self.addCleanup(p.stop)
        for nume in ("BRONZE_CAMPANII", "BRONZE_COMUNICATE"):
            p = mock.patch.object(C, nume, self.tmp.name)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(flux, "blocat", return_value=None)
        p.start()
        self.addCleanup(p.stop)
        self.jurnal = open(os.path.join(self.tmp.name, "j.jsonl"), "w", encoding="utf-8")
        self.addCleanup(self.jurnal.close)
        moment = datetime.datetime(2026, 9, 29, 12, 0, tzinfo=datetime.timezone.utc)
        self.col = C.Colector("x", self.CFG, moment, self.jurnal)
        self.col.colecteaza([], [])

    def test_excluderile_nu_se_cer(self):
        for u in self.cerute:
            self.assertIsNone(flux.motiv_excludere(u), u)
            self.assertNotIn("incheiat", u, "treapta A: arhivele nu se cer")
            self.assertNotIn("/en/", u)
        self.assertEqual(self.cerute, ["https://bank.ro/", "https://bank.ro/campanii",
                                       "https://bank.ro/campanii/card-cashback",
                                       "https://bank.ro/documente/regulament-cashback.pdf"])

    def test_campania_din_pagina_si_regulamentul_interzis(self):
        randuri = self.col.campanii()
        self.assertEqual(len(randuri), 1)
        r, leg = randuri[0]
        self.assertEqual(r["cheie"], "https://bank.ro/campanii/card-cashback")
        self.assertEqual((r["fereastra_start"], r["fereastra_sfarsit"]),
                         (datetime.date(2026, 9, 1), datetime.date(2026, 12, 31)))
        self.assertEqual((r["tip_oferta"], r["stare"], r["sursa_ferestrei"]), ("campanie", "activa", "document"))
        self.assertIn("200 lei", r["beneficiu"])
        self.assertEqual({x["rol_document"] for x in leg}, {"landing", "regulament", "hub"})
        # octeții în bronze/campanii (aici, directorul temporar), nu în bronze/
        pagina = next(x for x in leg if x["rol_document"] == "landing")
        self.assertTrue(pagina["amprenta"])

    def test_idempotenta_normalizarii(self):
        self.assertEqual(self.col.campanii(), self.col.campanii())


class TestSimulare(unittest.TestCase):
    def test_fara_nicio_cerere(self):
        import io
        out = io.StringIO()
        with mock.patch.object(transport, "adu", side_effect=_fara_retea), \
                mock.patch.object(flux, "reguli_pentru", side_effect=_fara_retea):
            rez = C.simuleaza(C.banci_de_rulat(None), False, out, cu_baza=False)
        text = out.getvalue()
        stari = {slug: stare for slug, stare, *_ in rez}
        for slug in K.BLOCATE:
            self.assertEqual(stari[slug], "blocat")
            self.assertRegex(text, rf"{re.escape(slug)}: BLOCAT — 0 cereri")
        self.assertEqual(len(rez), 30)
        self.assertIn("robots necunoscut încă", text)


class TestRegulileStauIntrUnLoc(unittest.TestCase):
    def _view(self, cale):
        with open(os.path.join(RADACINA, cale), encoding="utf-8") as f:
            text = f.read()
        m = re.search(r"CREATE VIEW campanii_curente AS(.*?);", text, re.S)
        return re.sub(r"\s+", " ", m.group(1)).strip()

    def test_vederea_identica_in_migrare_si_sincronizare(self):
        self.assertEqual(self._view("db/migration_019_campanii.sql"), self._view("db/sincronizeaza_vederi.sql"))

    def test_banci_reper_la_fel_in_sql(self):
        v = self._view("db/migration_019_campanii.sql")
        lista = set(re.findall(r"'([a-z-]+)'", re.search(r"b\.slug IN \(([^)]*)\)", v).group(1)))
        self.assertEqual(lista, set(K.BANCI_REPER))

    def test_din_bronze_filtreaza_rolul(self):
        with open(os.path.join(AICI, "populare_initiala.py"), encoding="utf-8") as f:
            text = f.read()
        corp = text[text.index("def din_bronze"):text.index("def completeaza_banca")]
        self.assertIn("s.rol IN ('produs', 'conditii', 'locator')", corp)

    def test_toate_bancile_au_o_stare(self):
        self.assertEqual(len(C.banci_de_rulat(None)), 30)


class TestScriereIdempotenta(unittest.TestCase):
    """Pe baza locală, doar dacă migrarea 019 e aplicată; totul se anulează."""

    def test_de_doua_ori_aceleasi_randuri(self):
        try:
            import psycopg2
            import normalizeaza as N
            conn = psycopg2.connect(N.dsn(), connect_timeout=3)
        except Exception as exc:
            self.skipTest(f"baza indisponibilă: {type(exc).__name__}")
        try:
            with conn.cursor() as cur:
                if not NC.migrarea_aplicata(cur):
                    self.skipTest("migrarea 019 nu e aplicată pe baza locală")
                u = "https://www.librabank.ro/test-campanie-idempotenta"
                membri = [{"url": u, "rol_document": "landing", "eticheta": "Test", "url_hub": None}]
                rand = NC.campanie(u, membri, {u: _docs(format="html")}, AZI, "hub")
                m1 = datetime.datetime(2026, 9, 29, 10, tzinfo=datetime.timezone.utc)
                m2 = datetime.datetime(2026, 9, 29, 11, tzinfo=datetime.timezone.utc)
                NC.scrie_campanii(cur, "libra", [rand], m1)
                NC.scrie_campanii(cur, "libra", [rand], m2)
                cur.execute("SELECT count(*), min(prima_vedere), max(ultima_vedere) FROM campanii WHERE cheie = %s", (u,))
                n, prima, ultima = cur.fetchone()
                cur.execute("""SELECT count(*) FROM campanii_surse cs JOIN campanii c ON c.id = cs.id_campanie
                               WHERE c.cheie = %s""", (u,))
                self.assertEqual((n, cur.fetchone()[0]), (1, 1))
                self.assertEqual((prima, ultima), (m1, m2))
        finally:
            conn.rollback()
            conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    unittest.main(verbosity=2)
