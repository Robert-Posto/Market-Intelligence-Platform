"""Teste de integrare pentru poarta de autentificare din app/server.py.

Serverul pornește pe un port liber, cu un AD simulat (verificatorul injectat în
`Autentificator`), fără bază de date: rutele de date folosite aici sunt înlocuite cu unele
false, ca „a trecut de poartă” să nu depindă de Postgres.

Rulare:  python app/test_server_autentificare.py
"""

import http.client
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import autentificare  # noqa: E402
import rulari  # noqa: E402

PAROLA = "Parola-Secreta-123!"
CONTURI = {"ana": (PAROLA, "Ana Analist", "analist"), "adi": (PAROLA, "Adi Admin", "admin"),
           "fara": (PAROLA, "Fără Rol", None)}
RUTE_ADMIN_GET = ["/api/jobs", "/api/rulare_manuala", "/api/rulare_manuala/estimare", "/api/rulari"]
RUTE_ADMIN_POST = ["/api/rulari/porneste", "/api/rulari/opreste"]
TEST_RULARI = [{"id": "nimic", "nume": "Nimic", "ce": "test", "argumente": ["-c", "import time; time.sleep(30)"],
                "banca": None, "internet": False, "estimare_min": 1}]
CONFIG_AD = autentificare.Config(url="ldaps://dc01.banca.example:636", domeniu="banca.example",
                                 baza="DC=banca,DC=example", grup_admin="CN=MCC-Admin,DC=banca,DC=example",
                                 grup_analist="CN=MCC-Analist,DC=banca,DC=example")
VARIABILE = ("MCC_AUTH_LOCAL", "MCC_AUTH_OBLIGATORIE", "MIP_PERMITE_RULARI")


def verificator(utilizator, parola):
    if utilizator == "cade":
        raise ConnectionError(f"LDAPSocketOpenError: dc01.banca.example:636 refuzat (parola {parola})")
    cont = CONTURI.get(utilizator)
    if cont is None or cont[0] != parola:
        return None
    return cont[1], cont[2]


def port_liber():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.server_mod = server
        cls.dir = tempfile.mkdtemp(prefix="auth_http_")
        cls.mediu_vechi = {k: os.environ.get(k) for k in VARIABILE}
        cls.vechi = {k: getattr(server, k) for k in ("AUTENTIFICARE", "SESIUNI", "RULARI", "pdf_permis", "adu_pdf")}
        cls.rute_vechi = dict(server.RUTE)
        cls.jurnal_vechi = autentificare.CALE_JURNAL
        autentificare.CALE_JURNAL = os.path.join(cls.dir, "autentificare.log")
        server.SESIUNI = autentificare.Sesiuni()
        server.RULARI = rulari.Rulari(comenzi=TEST_RULARI, dir_rulari=cls.dir, slugs=lambda: ["bcr"])
        for cale in ("/api/sumar", "/api/jobs", "/api/rulare_manuala", "/api/rulare_manuala/estimare"):
            server.RUTE[cale] = lambda q, cale=cale: {"fals": cale}
        cls.pdf = os.path.join(cls.dir, "doc.pdf")
        with open(cls.pdf, "wb") as f:
            f.write(b"%PDF-1.4 test")
        server.pdf_permis = lambda url: True
        server.adu_pdf = lambda url: cls.pdf
        cls.srv = server.Server(("::", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        r = cls.server_mod.RULARI
        if r.curenta:
            r.opreste()
        cls.srv.shutdown()
        cls.srv.server_close()
        for k, v in cls.vechi.items():
            setattr(cls.server_mod, k, v)
        cls.server_mod.RUTE.clear()
        cls.server_mod.RUTE.update(cls.rute_vechi)
        autentificare.CALE_JURNAL = cls.jurnal_vechi
        for k, v in cls.mediu_vechi.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        # .env-ul de pe laptop poate avea MCC_AUTH_LOCAL; aici fiecare test își alege mediul
        for k in VARIABILE:
            os.environ.pop(k, None)
        os.environ["MIP_PERMITE_RULARI"] = "1"
        # AD configurat (fictiv, verificatorul e simulat): fără el, laptopul ar intra automat ca admin local
        self.server_mod.AUTENTIFICARE = autentificare.Autentificator(CONFIG_AD, verificator=verificator)

    def cere(self, metoda, cale, corp=None, antete=None, cookie=None, brut=None, nume_cookie="mcc_sesiune"):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": f"localhost:{self.port}"}
        if corp is not None:
            h["Content-Type"] = "application/json"
            brut = json.dumps(corp)
        if cookie:
            h["Cookie"] = f"{nume_cookie}={cookie}"
        h.update(antete or {})
        c.request(metoda, cale, body=brut, headers=h)
        r = c.getresponse()
        d = r.read().decode("utf-8", errors="replace")
        antete_r = {k.lower(): v for k, v in r.getheaders()}
        c.close()
        try:
            d = json.loads(d)
        except ValueError:
            pass
        return r.status, antete_r, d

    def logare(self, utilizator, parola=PAROLA, antete=None):
        cod, h, d = self.cere("POST", "/api/autentificare", {"utilizator": utilizator, "parola": parola}, antete)
        cookie = None
        if "set-cookie" in h:
            cookie = h["set-cookie"].split(";")[0].partition("=")[2]
        return cod, h, d, cookie

    def jurnal(self):
        try:
            with open(autentificare.CALE_JURNAL, encoding="utf-8") as f:
                return [json.loads(r) for r in f]
        except FileNotFoundError:
            return []

    # ---------------- poarta

    def test_fara_sesiune_401_peste_tot(self):
        for cale in ("/api/sumar", "/api/jobs", "/api/rulari", "/api/rulare_manuala", "/api/necunoscut",
                     "/pdf?u=https://banca.example/a.pdf", "/logos/x.svg", "/pdf.html", "/harta.html", "/",
                     "/index.html", "/server.py", "/rulari.py", "//api/sumar", "/api/sumar/"):
            cod, h, d = self.cere("GET", cale)
            self.assertEqual((cod, d), (401, {"eroare": "neautentificat"}), cale)
            self.assertEqual(h.get("cache-control"), "no-store", cale)
        for cale in RUTE_ADMIN_POST + ["/api/altceva"]:
            self.assertEqual(self.cere("POST", cale, {})[0], 401, cale)
        self.assertEqual(self.cere("HEAD", "/pdf.html")[0], 401)
        # un GET care anunță un corp pe care nu-l trimite nu ține firul (nu se citește)
        self.assertEqual(self.cere("GET", "/api/sumar", antete={"Content-Length": "100"})[0], 401)
        self.assertEqual(self.cere("HEAD", "/server.py")[0], 401)
        self.assertIsNone(self.server_mod.RULARI.curenta)

    def test_rutele_publice(self):
        self.assertEqual(self.cere("GET", "/api/sesiune"), (401, unittest.mock.ANY, {"eroare": "neautentificat"}))
        cod, _, _ = self.cere("GET", "/app/")           # interfața construită: pagina de logare
        self.assertNotIn(cod, (401, 403))
        # prefixul public /app/ nu duce în afara web/dist (la sursele din app/, de pildă)
        for cale in ("/app/../server.py", "/app/..%2fserver.py", "/app/..%5cserver.py",
                     "/app/%2e%2e/%2e%2e/config.py", "/app/../pdf.html"):
            cod, _, d = self.cere("GET", cale)
            self.assertEqual(cod, 404, cale)
            self.assertNotIn("import", str(d), cale)
        cod, h, d = self.cere("POST", "/api/delogare", {})
        self.assertEqual((cod, d), (200, {}))

    # ---------------- logarea și cookie-ul

    def test_logare_si_cookie(self):
        cod, h, d, cookie = self.logare("ana")
        self.assertEqual(cod, 200)
        self.assertEqual(d, {"utilizator": "ana", "nume": "Ana Analist", "rol": "analist"})
        self.assertEqual(h.get("cache-control"), "no-store")
        parti = [p.strip() for p in h["set-cookie"].split(";")]
        self.assertTrue(parti[0].startswith("mcc_sesiune=") and len(cookie) >= 43)
        self.assertEqual(set(parti[1:]), {"HttpOnly", "SameSite=Strict", "Path=/", "Max-Age=43200"})
        self.assertNotIn(PAROLA, json.dumps(self.jurnal()))
        # pe HTTPS (nginx pune X-Forwarded-Proto): __Host-, deci Secure, Path=/ și fără Domain
        _, h, _, _ = self.logare("ana", antete={"X-Forwarded-Proto": "https", "X-Real-IP": "10.0.0.5"})
        parti = [p.strip() for p in h["set-cookie"].split(";")]
        self.assertTrue(parti[0].startswith("__Host-mcc_sesiune="))
        self.assertEqual(set(parti[1:]), {"HttpOnly", "SameSite=Strict", "Path=/", "Max-Age=43200", "Secure"})

    def test_cookie_host_pe_https(self):
        """Pe HTTPS contează doar __Host-mcc_sesiune: un mcc_sesiune pus de alt *.libra.bank nu se citește."""
        https = {"X-Forwarded-Proto": "https", "X-Real-IP": "10.0.0.5"}
        _, _, _, sid = self.logare("ana", antete=https)
        cod, _, d = self.cere("GET", "/api/sesiune", antete=https, cookie=sid, nume_cookie="__Host-mcc_sesiune")
        self.assertEqual((cod, d["utilizator"]), (200, "ana"))
        # același identificator sub celălalt nume: refuzat, pe fiecare schemă
        self.assertEqual(self.cere("GET", "/api/sumar", antete=https, cookie=sid)[0], 401)
        self.assertEqual(self.cere("GET", "/api/sumar", cookie=sid, nume_cookie="__Host-mcc_sesiune")[0], 401)
        _, _, _, sid_http = self.logare("adi")
        self.assertEqual(self.cere("GET", "/api/sumar", antete=https, cookie=sid_http)[0], 401)
        self.assertEqual(self.cere("GET", "/api/sumar", cookie=sid_http)[0], 200)
        # ieșirea pe HTTPS golește cookie-ul __Host- (cu aceleași atribute, altfel browserul îl ignoră)
        cod, h, _ = self.cere("POST", "/api/delogare", {}, antete=https, cookie=sid, nume_cookie="__Host-mcc_sesiune")
        parti = [p.strip() for p in h["set-cookie"].split(";")]
        self.assertEqual(parti[0], "__Host-mcc_sesiune=")
        self.assertTrue({"Max-Age=0", "Secure", "Path=/"} <= set(parti))
        self.assertEqual(self.cere("GET", "/api/sesiune", antete=https, cookie=sid,
                                   nume_cookie="__Host-mcc_sesiune")[0], 401)
        self.assertEqual(self.jurnal()[-1]["eveniment"], "delogare")

    def test_sesiune_cu_cookie(self):
        _, _, _, cookie = self.logare("ana")
        cod, h, d = self.cere("GET", "/api/sesiune", cookie=cookie)
        self.assertEqual((cod, d), (200, {"utilizator": "ana", "nume": "Ana Analist", "rol": "analist", "local": False}))
        self.assertEqual(self.cere("GET", "/api/sumar", cookie=cookie)[:3:2], (200, {"fals": "/api/sumar"}))

    def test_cookie_falsificat_sau_dublat(self):
        self.assertEqual(self.cere("GET", "/api/sumar", cookie="x" * 43)[0], 401)
        _, _, _, cookie = self.logare("ana")
        # un cookie cu același nume pus de alt subdomeniu nu blochează sesiunea bună
        cod, _, _ = self.cere("GET", "/api/sumar", antete={"Cookie": f"mcc_sesiune=fals; alt=1; mcc_sesiune={cookie}"})
        self.assertEqual(cod, 200)

    def test_identificator_nou_la_fiecare_logare(self):
        _, _, _, c1 = self.logare("ana")
        cod, h, d = self.cere("POST", "/api/autentificare", {"utilizator": "ana", "parola": PAROLA}, cookie=c1)
        c2 = h["set-cookie"].split(";")[0].partition("=")[2]
        self.assertNotEqual(c1, c2)
        self.assertEqual(self.cere("GET", "/api/sesiune", cookie=c1)[0], 401)   # cea veche nu mai merge
        self.assertEqual(self.cere("GET", "/api/sesiune", cookie=c2)[0], 200)

    def test_delogare(self):
        _, _, _, cookie = self.logare("adi")
        cod, h, d = self.cere("POST", "/api/delogare", {}, cookie=cookie)
        self.assertEqual((cod, d), (200, {}))
        parti = [p.strip() for p in h["set-cookie"].split(";")]
        self.assertEqual(parti[0], "mcc_sesiune=")
        self.assertIn("Max-Age=0", parti)
        self.assertEqual(self.cere("GET", "/api/sesiune", cookie=cookie)[0], 401)
        self.assertEqual(self.cere("GET", "/api/sumar", cookie=cookie)[0], 401)
        self.assertEqual(self.jurnal()[-1]["eveniment"], "delogare")
        self.assertEqual(self.jurnal()[-1]["utilizator"], "adi")

    # ---------------- codurile de eroare

    def test_coduri_de_eroare(self):
        self.assertEqual(self.logare("ana", "gresit")[:3:2], (401, {"eroare": "date_invalide"}))
        self.assertEqual(self.logare("fara")[:3:2], (403, {"eroare": "fara_rol"}))
        self.assertEqual(self.logare("*)(uid=*")[:3:2], (401, {"eroare": "date_invalide"}))
        self.assertEqual(self.logare("ana", "")[:3:2], (401, {"eroare": "date_invalide"}))
        cod, h, d = self.cere("POST", "/api/autentificare", {"utilizator": "ana"})
        self.assertEqual((cod, d), (401, {"eroare": "date_invalide"}))
        cod, h, d = self.cere("POST", "/api/autentificare", {"utilizator": 3, "parola": ["x"]})
        self.assertEqual((cod, d), (401, {"eroare": "date_invalide"}))
        for _ in range(4):
            self.logare("ana", "gresit")
        cod, h, d, cookie = self.logare("ana")
        self.assertEqual((cod, d, cookie), (429, {"eroare": "prea_multe_incercari"}, None))
        # AD-ul căzut: clientul vede doar codul, detaliul rămâne în jurnal
        cod, h, d, cookie = self.logare("cade")
        self.assertEqual((cod, d, cookie), (503, {"eroare": "ad_indisponibil"}, None))
        self.assertIn("dc01.banca.example", self.jurnal()[-1]["detaliu"])
        self.assertNotIn(PAROLA, json.dumps(self.jurnal(), ensure_ascii=False))

    def test_fara_ad_configurat_laptopul_intra_automat(self):
        # până vin datele de la IT: fără MCC_AUTH_LOCAL în .env, laptopul intră ca admin local
        self.server_mod.AUTENTIFICARE = autentificare.Autentificator(autentificare.Config())
        cod, _, d = self.cere("GET", "/api/sesiune")
        self.assertEqual((cod, d), (200, {"utilizator": "local", "nume": "local", "rol": "admin", "local": True}))
        self.assertEqual(self.cere("GET", "/api/jobs")[0], 200)
        # DNS rebinding (alt Host), nginx (X-Real-IP) sau serverul (MCC_AUTH_OBLIGATORIE): logare cerută
        self.assertEqual(self.cere("GET", "/api/sumar", antete={"Host": "evil.example:8765"})[0], 401)
        self.assertEqual(self.cere("GET", "/api/sumar", antete={"X-Real-IP": "10.0.0.5"})[0], 401)
        os.environ["MCC_AUTH_OBLIGATORIE"] = "1"
        self.assertEqual(self.cere("GET", "/api/sumar")[0], 401)

    def test_ad_neconfigurat_503(self):
        self.server_mod.AUTENTIFICARE = autentificare.Autentificator(autentificare.Config())
        self.assertEqual(self.logare("ana")[:3:2], (503, {"eroare": "ad_indisponibil"}))

    def test_ldap_real_inaccesibil_503_fara_detalii(self):
        """Drumul real (ldap3, fără verificator injectat) spre un port unde nu ascultă nimeni."""
        c = autentificare.Config(url="ldaps://127.0.0.1:1", domeniu="banca.example", baza="DC=banca,DC=example",
                                 grup_admin="CN=A,DC=banca,DC=example", grup_analist="CN=B,DC=banca,DC=example")
        self.assertIsNone(c.problema())
        self.server_mod.AUTENTIFICARE = autentificare.Autentificator(c)
        cod, h, brut = self.cere("POST", "/api/autentificare", {"utilizator": "ana", "parola": PAROLA})
        self.assertEqual((cod, brut), (503, {"eroare": "ad_indisponibil"}))
        self.assertNotIn("set-cookie", h)
        rand = self.jurnal()[-1]
        # încercare eșuată: doar amprenta numelui (numele scris poate fi o parolă)
        self.assertEqual((rand["motiv"], rand["utilizator_hash"]), ("indisponibil", autentificare.hash_utilizator("ana")))
        self.assertNotIn("utilizator", rand)
        self.assertIn("LDAPSocketOpenError", rand["detaliu"])
        self.assertNotIn(PAROLA, json.dumps(self.jurnal(), ensure_ascii=False))

    def test_ip_din_x_real_ip(self):
        for i in range(20):
            self.logare(f"u{i}", "gresit", {"X-Real-IP": "10.0.0.9"})
        self.assertEqual(self.logare("ana", antete={"X-Real-IP": "10.0.0.9"})[0], 429)
        self.assertEqual(self.logare("ana", antete={"X-Real-IP": "10.0.0.10"})[0], 200)
        self.assertEqual(self.jurnal()[-1]["ip"], "10.0.0.10")

    # ---------------- cerința 9: forma cererii

    def test_post_fara_json_415(self):
        for tip in ("application/x-www-form-urlencoded", "text/plain", "multipart/form-data; boundary=x"):
            for cale in ("/api/autentificare", "/api/delogare"):
                cod, _, _ = self.cere("POST", cale, antete={"Content-Type": tip}, brut="utilizator=ana&parola=x")
                self.assertEqual(cod, 415, (cale, tip))
        cod, _, _ = self.cere("POST", "/api/autentificare", brut="{}")       # fără Content-Type
        self.assertEqual(cod, 415)

    def test_sec_fetch_site(self):
        for site in ("cross-site", "same-site"):
            cod, _, d, cookie = self.logare("ana", antete={"Sec-Fetch-Site": site})
            self.assertEqual((cod, d, cookie), (403, {"eroare": "interzis"}, None), site)
            self.assertEqual(self.cere("POST", "/api/delogare", {}, antete={"Sec-Fetch-Site": site})[0], 403)
        for site in ("same-origin", "none"):
            self.assertEqual(self.logare("ana", antete={"Sec-Fetch-Site": site})[0], 200, site)

    def test_corp_prea_mare_sau_stricat(self):
        inainte = len(self.jurnal())
        # doar antetele: corpul de peste 2 KB nu se citește, deci nici nu se trimite (altfel RST)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.putrequest("POST", "/api/autentificare")
        c.putheader("Content-Type", "application/json")
        c.putheader("Content-Length", "3000")
        c.endheaders()
        r = c.getresponse()
        self.assertEqual((r.status, json.loads(r.read())), (413, {"eroare": "date_invalide"}))
        c.close()
        for brut in ("{", "[]", '"ana"', "\xff"):
            cod, _, d = self.cere("POST", "/api/autentificare", antete={"Content-Type": "application/json"}, brut=brut)
            self.assertEqual(cod, 400, brut)
        self.assertEqual(len(self.jurnal()), inainte)      # niciuna n-a ajuns la verificare

    def test_refuzul_unui_post_cu_corp_ajunge_la_client(self):
        """401/403 la un POST cu corp: răspunsul nu se pierde într-un RST (sesiune expirată)."""
        _, _, _, cookie = self.logare("ana")
        corp = {"id": "nimic", "umplutura": "x" * 1500}
        for _ in range(25):
            self.assertEqual(self.cere("POST", "/api/rulari/porneste", corp)[0], 401)
            self.assertEqual(self.cere("POST", "/api/rulari/porneste", corp, cookie=cookie)[0], 403)
            self.assertEqual(self.cere("POST", "/api/autentificare", antete={"Content-Type": "text/plain"},
                                       brut="utilizator=ana&parola=x" * 50)[0], 415)
            self.assertEqual(self.logare("ana", antete={"Sec-Fetch-Site": "cross-site"})[0], 403)

    # ---------------- rolurile

    def test_analist_403_pe_rutele_admin(self):
        _, _, _, cookie = self.logare("ana")
        for cale in RUTE_ADMIN_GET + ["/api/rulare_manuala/estimare?tip=discovery"]:
            self.assertEqual(self.cere("GET", cale, cookie=cookie)[:3:2], (403, {"eroare": "interzis"}), cale)
        for cale in RUTE_ADMIN_POST:
            cod, _, d = self.cere("POST", cale, {"id": "nimic"}, cookie=cookie)
            self.assertEqual((cod, d), (403, {"eroare": "interzis"}), cale)
        self.assertIsNone(self.server_mod.RULARI.curenta)
        refuzuri = [r for r in self.jurnal() if r["eveniment"] == "refuz_admin"]
        self.assertEqual(len(refuzuri), 7)
        self.assertEqual({r["utilizator"] for r in refuzuri}, {"ana"})
        self.assertIn("/api/rulari/porneste", {r["cale"] for r in refuzuri})

    def test_admin_trece_si_jurnalul_rularilor(self):
        _, _, _, cookie = self.logare("adi")
        for cale in RUTE_ADMIN_GET[:3]:
            self.assertEqual(self.cere("GET", cale, cookie=cookie)[:3:2], (200, {"fals": cale}))
        cod, _, stare = self.cere("GET", "/api/rulari", cookie=cookie)
        self.assertEqual(cod, 200)
        token = stare["token"]
        cod, _, d = self.cere("POST", "/api/rulari/porneste", {"id": "nimic"}, {"X-MIP-Token": token}, cookie=cookie)
        self.assertEqual(cod, 200, d)
        cod, _, d = self.cere("POST", "/api/rulari/opreste", {}, {"X-MIP-Token": token}, cookie=cookie)
        self.assertEqual(cod, 200, d)
        rulari_j = [r for r in self.jurnal() if r["eveniment"] in ("rulare_pornita", "rulare_oprita")]
        self.assertEqual([(r["eveniment"], r["utilizator"], r["id"]) for r in rulari_j],
                         [("rulare_pornita", "adi", "nimic"), ("rulare_oprita", "adi", "nimic")])
        t = time.time() + 15
        while self.server_mod.RULARI.curenta and time.time() < t:
            time.sleep(0.1)

    # ---------------- cerința 12

    def test_cache_control(self):
        _, _, _, cookie = self.logare("ana")
        cod, h, _ = self.cere("GET", "/pdf?u=https://banca.example/a.pdf", cookie=cookie)
        self.assertEqual((cod, h.get("cache-control")), (200, "private, max-age=86400"))
        cod, h, _ = self.cere("GET", "/api/sumar", cookie=cookie)
        self.assertEqual((cod, h.get("cache-control")), (200, "no-store"))

    # ---------------- cerința 11: scurtătura locală

    def test_mod_local(self):
        os.environ["MCC_AUTH_LOCAL"] = "admin"
        cod, _, d = self.cere("GET", "/api/sesiune")
        self.assertEqual((cod, d), (200, {"utilizator": "local", "nume": "local", "rol": "admin", "local": True}))
        self.assertEqual(self.cere("GET", "/api/jobs")[0], 200)
        # interfața veche de pe laptop merge ca înainte
        for cale in ("/", "/index.html", "/pdf.html", "/harta.html"):
            self.assertEqual(self.cere("GET", cale)[0], 200, cale)
        self.assertEqual(self.cere("HEAD", "/index.html")[0], 200)
        # prin nginx (X-Real-IP), niciodată local
        self.assertEqual(self.cere("GET", "/api/sesiune", antete={"X-Real-IP": "127.0.0.1"})[0], 401)
        self.assertEqual(self.cere("GET", "/api/jobs", antete={"X-Real-IP": "10.0.0.5"})[0], 401)
        os.environ["MCC_AUTH_OBLIGATORIE"] = "1"
        self.assertEqual(self.cere("GET", "/api/sesiune")[0], 401)
        self.assertEqual(self.cere("GET", "/api/sumar")[0], 401)
        del os.environ["MCC_AUTH_OBLIGATORIE"]
        os.environ["MCC_AUTH_LOCAL"] = "analist"
        self.assertEqual(self.cere("GET", "/api/jobs")[:3:2], (403, {"eroare": "interzis"}))
        self.assertEqual(self.cere("GET", "/api/sumar")[0], 200)

    # ---------------- fișierele statice (auditul de securitate, B5)

    def test_fisiere_statice_doar_din_lista(self):
        # cu sesiune (modul local): poarta trece, deci 404-ul vine din lista albă
        os.environ["MCC_AUTH_LOCAL"] = "admin"
        for cale in ("/C:/Windows/win.ini", "/../config.py", "/server.py", "/rulari.py", "/logos/../server.py",
                     "/logos/..%5cserver.py", "/logos/", "/__pycache__/", "/autentificare.py", "/logos",
                     "/logos/%2e%2e/server.py", "/C:%5cWindows%5cwin.ini", "/logos/CON.svg",
                     "/logos/..%2f..%2fconfig.py", "/app/assets/", "/%2e%2e/config.py"):
            cod, _, d = self.cere("GET", cale)
            self.assertEqual(cod, 404, cale)
            self.assertNotIn("import", str(d), cale)
            self.assertEqual(self.cere("HEAD", cale)[0], 404, cale)
        sigla = sorted(os.listdir(os.path.join(AICI, "logos")))[0]
        for cale in ("/", "/index.html", "/pdf.html", "/harta.html", "/favicon.ico",
                     f"/logos/{sigla}", f"/logos/{sigla}?v=1"):
            self.assertEqual(self.cere("GET", cale)[0], 200, cale)

    def test_pdf_erori_fara_detalii(self):
        # motivul (robots, adresă internă, textul băncii) rămâne în jurnalul serverului, nu la client;
        # mesajul cu diacritice rupea linia de stare (latin-1)
        os.environ["MCC_AUTH_LOCAL"] = "admin"
        vechi = self.server_mod.adu_pdf
        try:
            for exc, cod in ((PermissionError("interzis de robots.txt al băncii"), 403),
                             (PermissionError("x.ro duce la o adresă care nu e publică (10.0.0.5)"), 403),
                             (ValueError("HTTP 500: țâșnește de la 10.0.0.5"), 502)):
                def arunca(url, exc=exc):
                    raise exc
                self.server_mod.adu_pdf = arunca
                with unittest.mock.patch("sys.stderr", new_callable=io.StringIO) as jurnal:
                    c, _, d = self.cere("GET", "/pdf?u=https://banca.example/a.pdf")
                self.assertEqual(c, cod, exc)
                for detaliu in ("robots", "10.0.0.5", "500"):
                    self.assertNotIn(detaliu, str(d), exc)
                self.assertIn("/pdf", jurnal.getvalue())
        finally:
            self.server_mod.adu_pdf = vechi


class Pornire(unittest.TestCase):
    """`python app/server.py` ca proces: refuzul de pornire și motivul scris la pornire."""

    def mediu(self, **extra):
        env = {k: v for k, v in os.environ.items() if not k.startswith("MCC_")}
        env.update(PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", MIP_PORT=str(port_liber()), **extra)
        return env

    def test_refuza_pornirea_cu_local_si_obligatorie(self):
        p = subprocess.run([sys.executable, os.path.join(AICI, "server.py")], capture_output=True, timeout=60,
                           env=self.mediu(MCC_AUTH_OBLIGATORIE="1", MCC_AUTH_LOCAL="admin"))
        iesire = (p.stdout + p.stderr).decode("utf-8", errors="replace")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("MCC_AUTH_LOCAL", iesire)
        self.assertNotIn("MIP viewer", iesire)

    def test_scrie_la_pornire_de_ce_nu_merge_logarea(self):
        p = subprocess.Popen([sys.executable, os.path.join(AICI, "server.py")], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, env=self.mediu(MCC_LDAP_URL="ldap://dc01.banca.example"))
        randuri = []
        # readline blochează: dacă serverul nu scrie nimic, îl oprește cronometrul (EOF)
        cronometru = threading.Timer(60, p.kill)
        cronometru.start()
        try:
            while True:
                r = p.stdout.readline().decode("utf-8", errors="replace")
                if not r:
                    break
                randuri.append(r)
                if "MIP viewer" in r:
                    break
        finally:
            cronometru.cancel()
            p.kill()
            p.wait()
            p.stdout.close()
        iesire = "".join(randuri)
        self.assertIn("MIP viewer", iesire)
        self.assertIn("ldaps", iesire)


if __name__ == "__main__":
    unittest.main(verbosity=2)
