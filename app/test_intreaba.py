"""Teste offline pentru „Întreabă datele” (app/intreaba.py și rutele din server).

Fără rețea și fără cheie: modelul e un client fals, care întoarce JSON-ul dat de test.

Rulare:  python app/test_intreaba.py
"""

import http.client
import json
import os
import sys
import tempfile
import threading
import types
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import intreaba  # noqa: E402

CTX = {
    "banci": [{"slug": "bcr", "nume": "BCR"}, {"slug": "brd", "nume": "BRD"},
              {"slug": "ing", "nume": "ING Bank"}, {"slug": "libra", "nume": "Libra Internet Bank"}],
    "concepte": [
        {"camp": "administrare_cont", "n": 997, "unitati": ["eur", "lei"], "categorii": ["comision"],
         "exemple": ["Administrare cont curent", "Comision lunar de administrare"]},
        {"camp": "nominala", "n": 290, "unitati": ["procent"], "categorii": ["credite", "depozite"],
         "exemple": ["Depozit la termen 12 luni"]},
    ],
    "categorii": {"depozite": "Dobânzi la depozite", "credite": "Dobânzi la credite",
                  "conturi_carduri": "Conturi și carduri"},
    "concepte_categorie": {"depozite": ["nominala"], "credite": ["nominala", "dae", "marja_ircc"],
                           "conturi_carduri": ["nominala", "comision_procent"]},
    "termene": {"scurt": "1–3 luni", "6": "4–6 luni", "12": "7–12 luni", "lung": "peste 12 luni",
                "necunoscut": "termen nespecificat"},
    "produse": {"ipotecar": "Ipotecar / imobiliar", "nevoi_personale": "Nevoi personale",
                "card": "Card de credit / overdraft", "rate_magazin": "Rate fără dobândă în magazine",
                "altele": "Nespecificat în sursă"},
}


def interp(**k):
    baza = {"tip": "cautare", "banci": ["bcr"], "concept": "administrare_cont", "categorie": None,
            "termen": None, "produs_credit": None, "text_cautat": None, "clarificare": None}
    baza.update(k)
    return baza


def rand(valoare, unitate="lei", scenariu="comision|x", ambiguu=False):
    return {"valoare": valoare, "unitate": unitate, "cod_scenariu": scenariu, "ambiguu": ambiguu}


class ClientFals:
    """Un client Anthropic fals: întoarce JSON-ul dat și ține minte cererile."""

    def __init__(self, raspuns=None, stop="end_turn", exceptie=None):
        self.cereri = []
        self._raspuns, self._stop, self._exceptie = raspuns, stop, exceptie
        self.messages = self

    def create(self, **kw):
        self.cereri.append(kw)
        if self._exceptie:
            raise self._exceptie
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=json.dumps(self._raspuns))],
            stop_reason=self._stop,
            usage=types.SimpleNamespace(input_tokens=1200, output_tokens=60,
                                        cache_read_input_tokens=7000, cache_creation_input_tokens=0))


def fara_init(clasa, **atribute):
    """O excepție a SDK-ului fără răspunsul HTTP real: serverul se uită doar la clasă și la status_code."""
    e = clasa.__new__(clasa)
    for k, v in atribute.items():
        setattr(e, k, v)
    return e


class Configurare(unittest.TestCase):
    def setUp(self):
        self.vechi = {k: os.environ.get(k)
                      for k in ("MIP_PERMITE_INTREBARI", "ANTHROPIC_API_KEY", "MIP_INTREABA_MODEL")}

    def tearDown(self):
        for k, v in self.vechi.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_activ_cere_variabila_si_cheie_reala(self):
        os.environ["MIP_PERMITE_INTREBARI"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90
        self.assertTrue(intreaba.activ())
        for cheie in ("", "placehold1", "sk-ant-...", "sk-ant-scurt"):
            os.environ["ANTHROPIC_API_KEY"] = cheie
            self.assertFalse(intreaba.activ(), cheie)
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90
        os.environ["MIP_PERMITE_INTREBARI"] = "0"
        self.assertFalse(intreaba.activ())

    def test_model_implicit_haiku(self):
        os.environ.pop("MIP_INTREABA_MODEL", None)
        self.assertEqual(intreaba.model(), "claude-haiku-4-5")
        os.environ["MIP_INTREABA_MODEL"] = "claude-sonnet-5-5"
        self.assertEqual(intreaba.model(), "claude-sonnet-5-5")


class Intrare(unittest.TestCase):
    def test_intrebarea(self):
        self.assertEqual(intreaba.verifica_intrebarea("  Cât costă?  "), "Cât costă?")
        self.assertEqual(len(intreaba.verifica_intrebarea("a" * 500)), 500)
        for rau in ("", "   ", None, 3, ["x"], "a" * 501):
            with self.assertRaises(intreaba.Respins):
                intreaba.verifica_intrebarea(rau)

    def test_anterior(self):
        self.assertIsNone(intreaba.verifica_anterior(None))
        self.assertEqual(intreaba.verifica_anterior(interp())["concept"], "administrare_cont")
        for rau in ("text", ["x"], {"tip": "cautare", "altceva": 1}, interp(text_cautat="x" * 2000)):
            with self.assertRaises(intreaba.Respins):
                intreaba.verifica_anterior(rau)


class Schema(unittest.TestCase):
    def test_enum_din_liste(self):
        s = intreaba.schema(CTX)
        p = s["properties"]
        self.assertEqual(p["banci"]["items"]["enum"], ["bcr", "brd", "ing", "libra"])
        self.assertEqual(p["concept"]["anyOf"][0]["enum"], ["administrare_cont", "nominala"])
        self.assertEqual(p["termen"]["anyOf"][0]["enum"], list(CTX["termene"]))
        self.assertEqual(sorted(s["required"]), sorted(intreaba.CHEI))
        self.assertIs(s["additionalProperties"], False)

    def test_prompt_contine_listele_si_regula(self):
        text = intreaba.prompt(CTX)
        self.assertIn("ing: ING Bank", text)
        self.assertIn("administrare_cont · eur, lei · comision · 997 · Administrare cont curent", text)
        self.assertIn("NU răspunzi", text)
        # „Ce dobândă dă ING la depozitul pe 12 luni?” ieșea fără concept (06.10.2026, live): slug-ul
        # `nominala` nu spune „dobândă”, deci fiecare categorie își arată conceptele
        self.assertIn("depozite (Dobânzi la depozite; concepte: nominala)", text)
        # „și la BRD?” după BCR dădea [bcr, brd] (live): continuarea înlocuiește banca
        self.assertIn("înlocuiește băncile anterioare", text)
        # identic la fiecare apel: cache-ul promptului cere un prefix stabil
        self.assertEqual(text, intreaba.prompt(CTX))


class Validare(unittest.TestCase):
    def test_bun(self):
        curat, ignorate = intreaba.valideaza(interp(banci=["bcr", "brd"]), CTX)
        self.assertEqual((curat["tip"], curat["banci"], ignorate), ("cautare", ["bcr", "brd"], []))

    def test_dubluri_si_peste_trei(self):
        curat, ignorate = intreaba.valideaza(interp(banci=["bcr", "bcr", "brd", "ing", "libra"]), CTX)
        self.assertEqual(curat["banci"], ["bcr", "brd", "ing"])
        self.assertEqual(ignorate, ["libra"])

    def test_slug_sau_enum_inexistent(self):
        for rau in (interp(banci=["nu-exista"]), interp(concept="inventat"), interp(categorie="comision"),
                    interp(termen="24"), interp(produs_credit="leasing"), interp(tip="altul"), None, "x"):
            curat, _ = intreaba.valideaza(rau, CTX)
            self.assertEqual(curat["tip"], "neclar", rau)
            self.assertIsNone(curat["clarificare"], rau)
            self.assertEqual(curat["banci"], [], rau)

    def test_cautare_fara_banca_sau_fara_ce(self):
        self.assertEqual(intreaba.valideaza(interp(banci=[]), CTX)[0]["tip"], "neclar")
        self.assertEqual(intreaba.valideaza(interp(concept=None, text_cautat=None), CTX)[0]["tip"], "neclar")
        self.assertEqual(intreaba.valideaza(interp(concept=None, text_cautat="   "), CTX)[0]["tip"], "neclar")
        curat, _ = intreaba.valideaza(interp(concept=None, text_cautat="  datoria vamală "), CTX)
        self.assertEqual((curat["tip"], curat["text_cautat"]), ("cautare", "datoria vamală"))

    def test_clarificare_pastrata(self):
        curat, _ = intreaba.valideaza(
            interp(tip="neclar", banci=[], concept=None, clarificare="La ce bancă?"), CTX)
        self.assertEqual(curat["clarificare"], "La ce bancă?")


class Rezumat(unittest.TestCase):
    def test_pe_unitate_fara_ambigue(self):
        r = intreaba.rezuma([rand(0), rand(5), rand(15), rand(999, ambiguu=True), rand(2, "eur"), rand(None)])
        self.assertEqual(r[0], {"unitate": "lei", "categorie": "comision", "n": 3,
                                "minim": 0, "maxim": 15, "gratuite": 1})
        self.assertEqual(r[1]["unitate"], "eur")
        self.assertEqual(len(r), 2)

    def test_dobanzi_de_depozit_si_credit_separat(self):
        """`nominala` fără categorie: dobânzile de depozit și de credit nu ajung în același interval."""
        r = intreaba.rezuma([rand(6.5, "procent", "depozite|12"), rand(9.9, "procent", "credite|ipotecar")])
        self.assertEqual({(x["categorie"], x["maxim"]) for x in r}, {("depozite", 6.5), ("credite", 9.9)})


class Intrebari(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="intreaba_test_")
        self.cautari = []
        self.randuri = {"bcr": [rand(0), rand(15)], "brd": []}
        self.model_vechi = os.environ.pop("MIP_INTREABA_MODEL", None)

    def tearDown(self):
        if self.model_vechi is not None:
            os.environ["MIP_INTREABA_MODEL"] = self.model_vechi

    def fa(self, client, stare_banca=lambda b: None):
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((banca, concept, categorie, termen, produs, text))
            return self.randuri.get(banca, [])
        return intreaba.Intrebari(context=lambda: CTX, cauta=cauta, stare_banca=stare_banca,
                                  client=client, dir_jurnal=self.dir)

    def test_cautare_pe_concept(self):
        c = ClientFals(interp(banci=["bcr"]))
        d = self.fa(c).intreaba("Cât costă administrarea contului la BCR?")
        self.assertEqual(self.cautari, [("bcr", "administrare_cont", None, None, None, None)])
        r = d["raspunsuri"][0]
        self.assertEqual((r["banca"], r["mod"], r["total"], r["stare_banca"]), ("bcr", "concept", 2, None))
        self.assertEqual(r["rezumat"][0]["maxim"], 15)
        self.assertEqual(d["model"], "claude-haiku-4-5")
        self.assertEqual(d["tokeni"], {"intrare": 1200, "iesire": 60, "citire_cache": 7000, "scriere_cache": 0})
        self.assertAlmostEqual(d["cost_usd"], (1200 * 1 + 60 * 5 + 7000 * 0.1) / 1e6)
        cerere = c.cereri[0]
        self.assertEqual(cerere["model"], "claude-haiku-4-5")
        self.assertNotIn("thinking", cerere)                       # Haiku 4.5: fără gândire extinsă
        self.assertEqual(set(cerere["output_config"]), {"format"})  # și fără `effort`, care dă eroare
        self.assertEqual(cerere["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(cerere["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertEqual(cerere["messages"],
                         [{"role": "user", "content": "Cât costă administrarea contului la BCR?"}])

    def test_cautare_dupa_text(self):
        self.fa(ClientFals(interp(concept=None, text_cautat="datoria vamală"))).intreaba("vama la BCR?")
        self.assertEqual(self.cautari, [("bcr", None, None, None, None, "datoria vamală")])

    def test_anterior_ajunge_la_model(self):
        c = ClientFals(interp(banci=["brd"]))
        self.fa(c).intreaba("și la BRD?", interp())
        continut = c.cereri[0]["messages"][0]["content"]
        self.assertIn('"concept": "administrare_cont"', continut)
        self.assertIn("și la BRD?", continut)

    def test_zero_valori_spune_de_ce(self):
        d = self.fa(ClientFals(interp(banci=["brd"])), stare_banca=lambda b: "blocata").intreaba("BRD?")
        self.assertEqual((d["raspunsuri"][0]["total"], d["raspunsuri"][0]["stare_banca"]), (0, "blocata"))

    def test_multe_randuri_taiate_la_50(self):
        self.randuri["bcr"] = [rand(i) for i in range(120)]
        r = self.fa(ClientFals(interp())).intreaba("BCR?")["raspunsuri"][0]
        self.assertEqual((r["total"], len(r["randuri"]), r["rezumat"][0]["n"], r["limitat"]), (120, 50, 120, False))

    def test_text_limitat(self):
        self.randuri["bcr"] = [rand(i) for i in range(50)]
        r = self.fa(ClientFals(interp(concept=None, text_cautat="vamală"))).intreaba("BCR?")["raspunsuri"][0]
        self.assertTrue(r["limitat"])

    def test_in_afara_si_neclar_fara_cautare(self):
        for brut in (interp(tip="in_afara", banci=[]), interp(tip="neclar", banci=[], clarificare="Ce bancă?")):
            d = self.fa(ClientFals(brut)).intreaba("ceva")
            self.assertEqual(d["raspunsuri"], [])
        self.assertEqual(self.cautari, [])

    def test_refuz_sau_taiat_devine_neclar(self):
        for stop in ("refusal", "max_tokens"):
            d = self.fa(ClientFals(interp(), stop=stop)).intreaba("BCR?")
            self.assertEqual(d["interpretare"]["tip"], "neclar")
        self.assertEqual(self.cautari, [])

    def test_erorile_modelului(self):
        import anthropic
        cazuri = [
            (fara_init(anthropic.AuthenticationError, status_code=401), "401"),
            (fara_init(anthropic.RateLimitError, status_code=429), "429"),
            (fara_init(anthropic.APITimeoutError), "30 s"),
            (fara_init(anthropic.APIConnectionError), "api.anthropic.com"),
            (fara_init(anthropic.InternalServerError, status_code=529), "529"),
        ]
        for exc, text in cazuri:
            with self.assertRaises(intreaba.EroareModel) as e:
                self.fa(ClientFals(exceptie=exc)).intreaba("BCR?")
            self.assertIn(text, str(e.exception))

    def test_jurnal(self):
        import anthropic
        self.fa(ClientFals(interp())).intreaba("BCR?")
        with self.assertRaises(intreaba.EroareModel):
            self.fa(ClientFals(exceptie=fara_init(anthropic.APIConnectionError))).intreaba("BRD?")
        fisiere = os.listdir(self.dir)
        self.assertEqual(len(fisiere), 1)
        self.assertRegex(fisiere[0], r"^\d{4}-\d{2}\.jsonl$")
        with open(os.path.join(self.dir, fisiere[0]), encoding="utf-8") as f:
            randuri = [json.loads(x) for x in f]
        self.assertEqual([r["intrebare"] for r in randuri], ["BCR?", "BRD?"])
        self.assertEqual(randuri[0]["randuri"], {"bcr": 2})
        self.assertIn("api.anthropic.com", randuri[1]["eroare"])

    def test_stare_si_token(self):
        q = self.fa(ClientFals(interp()))
        self.assertEqual(set(q.stare()), {"activ", "model"})
        self.assertGreaterEqual(len(q.token), 32)
        self.assertNotEqual(q.token, self.fa(ClientFals(interp())).token)


class CuvinteCautare(unittest.TestCase):
    def test_cuvinte_cautare(self):
        import server
        self.assertEqual(server._cuvinte_cautare("Plată facturi"), ["plat", "factu"])
        self.assertEqual(server._cuvinte_cautare("ȘTERGERE Ţară"), ["sterge", "tara"])
        # niciun wildcard LIKE (%, _) și niciun semn ajung în parametru
        self.assertEqual(server._cuvinte_cautare("100% gratuit_x'; drop--"), ["100", "gratu", "drop"])
        self.assertEqual(server._cuvinte_cautare("a de la card card"), ["card"])
        self.assertEqual(server._cuvinte_cautare("unu doi trei patru cinci sase sapte"),
                         ["unu", "doi", "trei", "patr", "cinc"])

    def test_flexiunea_romaneasca(self):
        """„datoria vamală” trebuie să găsească „datoriei vamale” (BCR, 13 valori): pe subșirul exact
        căutarea dădea 0 rânduri (măsurat pe mip, 06.10.2026)."""
        import server
        cuvinte = server._cuvinte_cautare("datoria vamală")
        self.assertEqual(cuvinte, ["dator", "vama"])
        self.assertTrue(all(c in "decontarea electronica a datoriei vamale" for c in cuvinte))
        self.assertEqual(server._cuvinte_cautare(None), [])
        self.assertEqual(server._cuvinte_cautare(""), [])


class Http(unittest.TestCase):
    """Rutele din server, pe un port liber, cu un client fals în locul modelului."""

    @classmethod
    def setUpClass(cls):
        import server
        cls.server_mod = server
        cls.vechi = server.INTREBARI
        cls.client = ClientFals(interp())
        server.INTREBARI = intreaba.Intrebari(
            context=lambda: CTX, cauta=lambda *a: [rand(5)], stare_banca=lambda b: None,
            client=cls.client, dir_jurnal=tempfile.mkdtemp(prefix="intreaba_http_"))
        cls.srv = server.Server(("::", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.env_vechi = {k: os.environ.get(k) for k in ("MIP_PERMITE_INTREBARI", "ANTHROPIC_API_KEY")}

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.server_mod.INTREBARI = cls.vechi
        for k, v in cls.env_vechi.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        os.environ["MIP_PERMITE_INTREBARI"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90

    def cere(self, metoda, cale, corp=None, antete=None, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": host or f"localhost:{self.port}"}
        if corp is not None:
            h["Content-Type"] = "application/json"
            corp = json.dumps(corp)
        h.update(antete or {})
        c.request(metoda, cale, body=corp, headers=h)
        r = c.getresponse()
        d = r.read().decode("utf-8")
        c.close()
        try:
            return r.status, json.loads(d)
        except ValueError:
            return r.status, d

    def token(self):
        return self.cere("GET", "/api/intreaba")[1]["token"]

    def test_get(self):
        cod, d = self.cere("GET", "/api/intreaba")
        self.assertEqual((cod, d["activ"], d["model"]), (200, True, "claude-haiku-4-5"))
        self.assertEqual(d["token"], self.server_mod.INTREBARI.token)
        self.assertNotEqual(d["token"], self.server_mod.RULARI.token)

    def test_get_inactiv_fara_token(self):
        os.environ["ANTHROPIC_API_KEY"] = "placehold1"
        cod, d = self.cere("GET", "/api/intreaba")
        self.assertEqual((cod, d["activ"]), (200, False))
        self.assertNotIn("token", d)

    def test_get_host_strain(self):
        self.assertEqual(self.cere("GET", "/api/intreaba", host=f"evil.com:{self.port}")[0], 403)

    def test_post_merge_si_din_vite(self):
        """Din `npm run dev`, proxy-ul Vite rescrie Host-ul la server, dar Origin rămâne :5173."""
        t = self.token()
        for origine in (f"http://localhost:{self.port}", "http://localhost:5173", "http://127.0.0.1:5173"):
            cod, d = self.cere("POST", "/api/intreaba", {"intrebare": "BCR?"},
                               {"X-MIP-Token": t, "Origin": origine, "Sec-Fetch-Site": "same-origin"})
            self.assertEqual(cod, 200, (origine, d))
            self.assertEqual(d["raspunsuri"][0]["banca"], "bcr")

    def test_post_refuzat(self):
        t = self.token()
        ok = {"X-MIP-Token": t}
        cazuri = [
            ({}, None),                                                   # fără token
            ({"X-MIP-Token": "gresit"}, None),                            # token greșit
            ({"X-MIP-Token": self.server_mod.RULARI.token}, None),        # tokenul rulărilor nu e bun aici
            (ok, f"evil.com:{self.port}"),                                # Host străin
            (ok, "localhost:5173"),                                       # Host-ul rămâne portul serverului
            (dict(ok, Origin="http://evil.com"), None),                   # Origin străin
            (dict(ok, Origin="http://localhost:5174"), None),             # alt port decât Vite
            (dict(ok, **{"Sec-Fetch-Site": "cross-site"}), None),
        ]
        n = len(self.client.cereri)
        for antete, host in cazuri:
            cod, _ = self.cere("POST", "/api/intreaba", {"intrebare": "BCR?"}, antete, host)
            self.assertEqual(cod, 403, (antete, host))
        self.assertEqual(len(self.client.cereri), n)   # niciun apel plătit

    def test_post_inactiv(self):
        t = self.token()
        os.environ["MIP_PERMITE_INTREBARI"] = "0"
        cod, d = self.cere("POST", "/api/intreaba", {"intrebare": "BCR?"}, {"X-MIP-Token": t})
        self.assertEqual(cod, 403)
        self.assertIn("MIP_PERMITE_INTREBARI", d["eroare"])

    def test_post_forma(self):
        ok = {"X-MIP-Token": self.token()}
        self.assertEqual(self.cere("POST", "/api/intreaba", {"intrebare": ""}, ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/intreaba", {"intrebare": "a" * 501}, ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/intreaba", ["BCR?"], ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/intreaba", {"intrebare": "x" * 5000}, ok)[0], 400)
        cod, _ = self.cere("POST", "/api/intreaba", None, dict(ok, **{"Content-Type": "text/plain"}))
        self.assertEqual(cod, 415)

    def test_eroare_model_502(self):
        import anthropic
        ok = {"X-MIP-Token": self.token()}
        vechi = self.server_mod.INTREBARI._client
        self.server_mod.INTREBARI._client = ClientFals(exceptie=fara_init(anthropic.APIConnectionError))
        try:
            cod, d = self.cere("POST", "/api/intreaba", {"intrebare": "BCR?"}, ok)
        finally:
            self.server_mod.INTREBARI._client = vechi
        self.assertEqual(cod, 502)
        self.assertIn("api.anthropic.com", d["eroare"])


class Preturi(unittest.TestCase):
    def test_modelele_de_ales_au_pret(self):
        """MIP_INTREABA_MODEL poate fi schimbat; fără preț, costul ar apărea „necunoscut”."""
        for m in ("claude-haiku-4-5", "claude-sonnet-5-5", "claude-opus-5-5"):
            self.assertIsNotNone(intreaba.preturi.cost(m, 1000, 100), m)
        self.assertAlmostEqual(intreaba.preturi.cost("claude-opus-5-5", 1_000_000, 0), 4.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
