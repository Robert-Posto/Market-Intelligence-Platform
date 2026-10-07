"""Teste offline pentru Vox (app/vox.py și rutele din server).

Fără rețea și fără cheie: modelul e un client fals, care întoarce JSON-ul dat de test.

Rulare:  python app/test_vox.py
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

import vox  # noqa: E402

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
                      for k in ("MIP_PERMITE_VOX", "ANTHROPIC_API_KEY", "MIP_VOX_MODEL")}

    def tearDown(self):
        for k, v in self.vechi.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_activ_cere_variabila_si_cheie_reala(self):
        os.environ["MIP_PERMITE_VOX"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90
        self.assertTrue(vox.activ())
        for cheie in ("", "placehold1", "sk-ant-...", "sk-ant-scurt"):
            os.environ["ANTHROPIC_API_KEY"] = cheie
            self.assertFalse(vox.activ(), cheie)
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90
        os.environ["MIP_PERMITE_VOX"] = "0"
        self.assertFalse(vox.activ())

    def test_timeout_spune_toata_asteptarea(self):
        """SDK-ul reîncearcă singur după timeout: cu 30 s și max_retries=2, „n-a răspuns în 30 s”
        venea după până la 90 s de „Se interpretează…” (a doua revizie, 07.10.2026)."""
        import anthropic
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90
        c = vox.Vox(context=lambda: CTX, cauta=lambda *a: [], stare_banca=lambda b: None)._clientul()
        asteptare = c.timeout * (c.max_retries + 1)
        self.assertIn(f"în {asteptare:g} s", vox.mesaj_eroare(fara_init(anthropic.APITimeoutError)))
        self.assertLessEqual(asteptare, 45)

    def test_model_implicit_haiku(self):
        os.environ.pop("MIP_VOX_MODEL", None)
        self.assertEqual(vox.model(), "claude-haiku-4-5")
        os.environ["MIP_VOX_MODEL"] = "claude-sonnet-5-5"
        self.assertEqual(vox.model(), "claude-sonnet-5-5")


class Intrare(unittest.TestCase):
    def test_intrebarea(self):
        self.assertEqual(vox.verifica_intrebarea("  Cât costă?  "), "Cât costă?")
        self.assertEqual(len(vox.verifica_intrebarea("a" * 500)), 500)
        for rau in ("", "   ", None, 3, ["x"], "a" * 501):
            with self.assertRaises(vox.Respins):
                vox.verifica_intrebarea(rau)

    def test_anterior(self):
        self.assertIsNone(vox.verifica_anterior(None))
        self.assertEqual(vox.verifica_anterior(interp())["concept"], "administrare_cont")
        for rau in ("text", ["x"], {"tip": "cautare", "altceva": 1}, interp(text_cautat="x" * 2000)):
            with self.assertRaises(vox.Respins):
                vox.verifica_anterior(rau)


class Schema(unittest.TestCase):
    def test_enum_din_liste(self):
        s = vox.schema(CTX)
        p = s["properties"]
        self.assertEqual(p["banci"]["items"]["enum"], ["bcr", "brd", "ing", "libra"])
        self.assertEqual(p["concept"]["anyOf"][0]["enum"], ["administrare_cont", "nominala"])
        self.assertEqual(p["termen"]["anyOf"][0]["enum"], list(CTX["termene"]))
        self.assertEqual(sorted(s["required"]), sorted(vox.CHEI))
        self.assertIs(s["additionalProperties"], False)

    def test_prompt_contine_listele_si_regula(self):
        text = vox.prompt(CTX)
        self.assertIn("ing: ING Bank", text)
        self.assertIn("administrare_cont · eur, lei · comision · 997 · Administrare cont curent", text)
        self.assertIn("NU răspunzi", text)
        # „Ce dobândă dă ING la depozitul pe 12 luni?” ieșea fără concept (06.10.2026, live): slug-ul
        # `nominala` nu spune „dobândă”, deci fiecare categorie își arată conceptele
        self.assertIn("depozite (Dobânzi la depozite; concepte: nominala)", text)
        # „și la BRD?” după BCR dădea [bcr, brd] (live): continuarea înlocuiește banca
        self.assertIn("înlocuiește băncile anterioare", text)
        # „datoria vamală la BCR” ieșea `neclar` cu text_cautat completat (evaluarea din 06.10.2026):
        # modelul nu vede tarifele, deci nu el decide dacă serviciul există
        self.assertIn("nu știi ce conțin tarifele", text)
        # „What is the APR on a Libra mortgage?” ieșea `nominala` (7,71–7,84% în loc de DAE 8,09–8,37%),
        # „incoming payment” la BRD ieșea `transfer_credit` în 2 evaluări din 4 (07.10.2026, live)
        self.assertIn("APR", text)
        self.assertIn("incoming", text)
        # identic la fiecare apel: cache-ul promptului cere un prefix stabil
        self.assertEqual(text, vox.prompt(CTX))


class Validare(unittest.TestCase):
    def test_bun(self):
        curat, ignorate = vox.valideaza(interp(banci=["bcr", "brd"]), CTX)
        self.assertEqual((curat["tip"], curat["banci"], ignorate), ("cautare", ["bcr", "brd"], []))

    def test_dubluri_si_peste_trei(self):
        curat, ignorate = vox.valideaza(interp(banci=["bcr", "bcr", "brd", "ing", "libra"]), CTX)
        self.assertEqual(curat["banci"], ["bcr", "brd", "ing"])
        self.assertEqual(ignorate, ["libra"])

    def test_slug_sau_enum_inexistent(self):
        for rau in (interp(banci=["nu-exista"]), interp(concept="inventat"), interp(categorie="comision"),
                    interp(termen="24"), interp(produs_credit="leasing"), interp(tip="altul"), None, "x"):
            curat, _ = vox.valideaza(rau, CTX)
            self.assertEqual(curat["tip"], "neclar", rau)
            self.assertIsNone(curat["clarificare"], rau)
            self.assertEqual(curat["banci"], [], rau)

    def test_cautare_fara_banca_sau_fara_ce(self):
        self.assertEqual(vox.valideaza(interp(banci=[]), CTX)[0]["tip"], "neclar")
        self.assertEqual(vox.valideaza(interp(concept=None, text_cautat=None), CTX)[0]["tip"], "neclar")
        self.assertEqual(vox.valideaza(interp(concept=None, text_cautat="   "), CTX)[0]["tip"], "neclar")
        curat, _ = vox.valideaza(interp(concept=None, text_cautat="  datoria vamală "), CTX)
        self.assertEqual((curat["tip"], curat["text_cautat"]), ("cautare", "datoria vamală"))

    def test_neclar_cu_banca_si_ce_devine_cautare(self):
        """Spec: `neclar` = lipsește banca sau valoarea. Haiku punea `neclar` pe „datoria vamală la
        BCR” cu text_cautat completat și o clarificare falsă („nu se găsește în tarifele BCR”),
        în 2 evaluări din 2 (06.10.2026), deși căutarea găsește 13 valori."""
        curat, _ = vox.valideaza(interp(tip="neclar", concept=None, text_cautat="datoriei vamale",
                                             clarificare="Termenul nu se găsește în tarifele BCR."), CTX)
        self.assertEqual((curat["tip"], curat["text_cautat"], curat["clarificare"]),
                         ("cautare", "datoriei vamale", None))
        curat, _ = vox.valideaza(interp(tip="neclar", clarificare="Debit sau credit?"), CTX)
        self.assertEqual((curat["tip"], curat["clarificare"]), ("cautare", None))

    def test_categoria_ramane_doar_unde_conceptul_are_valori(self):
        """Categoriile vin din GRUPURI_RATE, iar `administrare_cont` are valori doar sub `comision`:
        cu „conturi_carduri” lângă el, fișa spunea că BCR n-are comisionul, deși avea 570 de valori
        (a doua revizie, 07.10.2026). Fără concept (căutare după text), o categorie ar tăia la fel."""
        curat, _ = vox.valideaza(interp(categorie="conturi_carduri"), CTX)
        self.assertEqual((curat["tip"], curat["concept"], curat["categorie"]),
                         ("cautare", "administrare_cont", None))
        curat, _ = vox.valideaza(interp(concept=None, text_cautat="datoria vamală", categorie="credite"), CTX)
        self.assertEqual((curat["tip"], curat["categorie"]), ("cautare", None))
        curat, _ = vox.valideaza(interp(concept="nominala", categorie="depozite"), CTX)
        self.assertEqual(curat["categorie"], "depozite")

    def test_text_fara_cuvinte_de_cautat_e_neclar(self):
        """Cuvintele sub 3 litere nu se caută: cu text_cautat „PO”, căutarea nici nu rula, iar fișa
        spunea „Nu avem valori pentru căutare după text «PO» la BCR” (a doua revizie, 07.10.2026)."""
        curat, _ = vox.valideaza(interp(concept=None, text_cautat="PO"), CTX)
        self.assertEqual((curat["tip"], curat["text_cautat"]), ("neclar", None))
        curat, _ = vox.valideaza(interp(concept=None, text_cautat="PO la ATM"), CTX)
        self.assertEqual((curat["tip"], curat["text_cautat"]), ("cautare", "PO la ATM"))

    def test_clarificare_pastrata(self):
        curat, _ = vox.valideaza(
            interp(tip="neclar", banci=[], concept=None, clarificare="La ce bancă?"), CTX)
        self.assertEqual(curat["clarificare"], "La ce bancă?")


class Rezumat(unittest.TestCase):
    def test_pe_unitate_fara_ambigue(self):
        r = vox.rezuma([rand(0), rand(5), rand(15), rand(999, ambiguu=True), rand(2, "eur"), rand(None)])
        self.assertEqual(r[0], {"unitate": "lei", "categorie": "comision", "n": 3,
                                "minim": 0, "maxim": 15, "gratuite": 1})
        self.assertEqual(r[1]["unitate"], "eur")
        self.assertEqual(len(r), 2)

    def test_gratuite_doar_la_comisioane(self):
        """O dobândă de 0% nu e „gratuită”: pe mip erau 21 de dobânzi neambigue de 0% (review, 06.10.2026)."""
        r = vox.rezuma([rand(0, "procent", "conturi_carduri|x"), rand(0), rand(0, "lei", "comisioane|y")])
        self.assertEqual({x["categorie"]: x["gratuite"] for x in r},
                         {"conturi_carduri": 0, "comision": 1, "comisioane": 1})

    def test_dobanzi_de_depozit_si_credit_separat(self):
        """`nominala` fără categorie: dobânzile de depozit și de credit nu ajung în același interval."""
        r = vox.rezuma([rand(6.5, "procent", "depozite|12"), rand(9.9, "procent", "credite|ipotecar")])
        self.assertEqual({(x["categorie"], x["maxim"]) for x in r}, {("depozite", 6.5), ("credite", 9.9)})


class IstoricConversatii(unittest.TestCase):
    def setUp(self):
        self.rad = tempfile.mkdtemp(prefix="vox_ist_")
        self.ist = vox.Istoric(os.path.join(self.rad, "conversatii"))

    def raspuns(self, cost=0.0015):
        return {"interpretare": interp(), "ignorate": [], "raspunsuri": [], "model": "claude-haiku-4-5",
                "tokeni": {"intrare": 1, "iesire": 1, "citire_cache": 0, "scriere_cache": 0}, "cost_usd": cost}

    def test_lista_goala_fara_dosar(self):
        self.assertEqual(self.ist.lista(), [])

    def test_adauga_citeste_lista(self):
        a = self.ist.id_nou()
        self.assertTrue(vox.Istoric.valid(a))
        self.ist.adauga(a, "Cât costă administrarea contului la BCR?", self.raspuns(0.0147))
        self.ist.adauga(a, "și la BRD?", self.raspuns(0.0015))
        c = self.ist.citeste(a)
        self.assertEqual((c["titlu"], c["redenumita"], [t["intrebare"] for t in c["ture"]]),
                         ("Cât costă administrarea contului la BCR?", False,
                          ["Cât costă administrarea contului la BCR?", "și la BRD?"]))
        self.assertEqual(c["ture"][1]["raspuns"]["cost_usd"], 0.0015)
        (rez,) = self.ist.lista()
        self.assertEqual((rez["id"], rez["intrebari"], rez["texte"]), (a, 2, [t["intrebare"] for t in c["ture"]]))
        self.assertAlmostEqual(rez["cost_usd"], 0.0162)
        self.assertEqual((rez["inceputa"], rez["ultima"]), (c["ture"][0]["data"], c["ture"][1]["data"]))

    def test_lista_dupa_ultima_intrebare_si_ora_de_iarna(self):
        """Ordinea e după ora reală, nu după text: la ora de iarnă (25.10.2026) „03:10+02:00” vine
        după „03:30+03:00”, deși ca text e înainte."""
        a, b = self.ist.id_nou(), self.ist.id_nou()
        self.ist.adauga(a, "A?", self.raspuns(), data="2026-10-25T03:30:00+03:00")
        self.ist.adauga(b, "B?", self.raspuns(), data="2026-10-25T03:10:00+02:00")
        self.assertEqual([r["id"] for r in self.ist.lista()], [b, a])

    def test_redenumire(self):
        a, b = self.ist.id_nou(), self.ist.id_nou()
        self.ist.adauga(a, "Cât costă administrarea contului la BCR?", self.raspuns(), data="2026-10-07T12:37:00+03:00")
        self.ist.adauga(b, "Altă întrebare?", self.raspuns(), data="2026-10-07T12:40:00+03:00")
        self.assertEqual(self.ist.redenumeste(a, "  Administrare cont BCR "),
                         {"titlu": "Administrare cont BCR", "redenumita": True})
        self.ist.redenumeste(a, "Comisioane BCR")
        lista = self.ist.lista()
        self.assertEqual([r["id"] for r in lista], [b, a])        # redenumirea nu mută conversația
        self.assertEqual((lista[1]["titlu"], lista[1]["redenumita"]), ("Comisioane BCR", True))
        self.assertEqual(self.ist.redenumeste(a, "   "),
                         {"titlu": "Cât costă administrarea contului la BCR?", "redenumita": False})
        for rau in ("x" * 121, 42):
            with self.assertRaises(vox.Respins):
                self.ist.redenumeste(a, rau)
        with self.assertRaises(vox.ConversatieLipsa):
            self.ist.redenumeste(self.ist.id_nou(), "titlu")

    def test_sterge(self):
        a = self.ist.id_nou()
        self.ist.adauga(a, "A?", self.raspuns())
        self.ist.lista()
        self.assertTrue(self.ist.sterge(a))
        self.assertEqual((self.ist.citeste(a), self.ist.lista(), self.ist.sterge(a)), (None, [], False))

    def test_id_invalid_nu_atinge_discul(self):
        afara = os.path.join(self.rad, "secret.jsonl")
        with open(afara, "w", encoding="utf-8") as f:
            f.write(json.dumps({"data": "2026-10-07T12:00:00+03:00", "intrebare": "secret", "raspuns": None}) + "\n")
        for rau in ("../secret", "..\\secret", "ABCDEF0123456789", "abc", "0123456789abcdef0", "", None, 7):
            self.assertIsNone(self.ist.citeste(rau), rau)
            self.assertFalse(self.ist.sterge(rau), rau)
            self.assertFalse(self.ist.exista(rau), rau)
            with self.assertRaises(vox.ConversatieLipsa):
                self.ist.adauga(rau, "x", self.raspuns())
        self.assertTrue(os.path.exists(afara))

    def test_rand_stricat_sarit(self):
        """O scriere întreruptă lasă un rând neterminat: se sare el, nu toată conversația."""
        a = self.ist.id_nou()
        self.ist.adauga(a, "A?", self.raspuns())
        with open(os.path.join(self.ist.dir, a + ".jsonl"), "a", encoding="utf-8") as f:
            f.write('{"data": "2026-10-07T12:00:00+03:00", "intreb')
        self.assertEqual([t["intrebare"] for t in self.ist.citeste(a)["ture"]], ["A?"])
        self.assertEqual(self.ist.lista()[0]["intrebari"], 1)

    def test_scriere_taiata_in_mijlocul_unei_litere(self):
        """O scriere întreruptă poate tăia o literă de 2 octeți („â”): rândul stricat se sare, restul
        conversației și lista rămân de citit (revizia istoricului, 07.10.2026: toată lista cădea)."""
        a = self.ist.id_nou()
        self.ist.adauga(a, "Cât costă administrarea contului la BCR?", self.raspuns())
        with open(os.path.join(self.ist.dir, a + ".jsonl"), "ab") as f:
            f.write('{"data": "2026-10-07T12:00:00+03:00", "intrebare": "Câ'.encode("utf-8")[:-1])
        self.assertEqual([t["intrebare"] for t in self.ist.citeste(a)["ture"]],
                         ["Cât costă administrarea contului la BCR?"])
        self.assertEqual(self.ist.lista()[0]["intrebari"], 1)

    def test_lista_tine_minte_rezumatul(self):
        """Lista se cere după fiecare întrebare: un fișier neschimbat nu se recitește."""
        a = self.ist.id_nou()
        self.ist.adauga(a, "A?", self.raspuns())
        self.ist.lista()
        citiri, citeste = [], self.ist.citeste
        self.ist.citeste = lambda id: citiri.append(id) or citeste(id)
        self.ist.lista()
        self.assertEqual(citiri, [])
        self.ist.adauga(a, "B?", self.raspuns())
        self.assertEqual(self.ist.lista()[0]["intrebari"], 2)
        self.assertEqual(citiri, [a])


class Intrebari(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="vox_test_")
        self.cautari = []
        self.randuri = {"bcr": [rand(0), rand(15)], "brd": []}
        self.model_vechi = os.environ.pop("MIP_VOX_MODEL", None)

    def tearDown(self):
        if self.model_vechi is not None:
            os.environ["MIP_VOX_MODEL"] = self.model_vechi

    def fa(self, client, stare_banca=lambda b: None):
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((banca, concept, categorie, termen, produs, text))
            return self.randuri.get(banca, [])
        return vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=stare_banca,
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

    def test_zero_cu_termen_spune_cate_sunt_fara(self):
        """ING are 2 dobânzi la depozite, dar niciuna cu termen citit din text (mip_merge, 06.10.2026):
        „nu avem valori” fără asta s-ar citi „ING nu are depozite”."""
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append(termen)
            return [] if termen else [rand(3.5, "procent", "depozite"), rand(3.6, "procent", "depozite")]
        c = ClientFals(interp(banci=["ing"], concept="nominala", categorie="depozite", termen="12"))
        q = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: None,
                               client=c, dir_jurnal=self.dir)
        r = q.intreaba("ING, depozit pe 12 luni?")["raspunsuri"][0]
        self.assertEqual((r["total"], r["fara_filtre"], self.cautari), (0, 2, ["12", None]))

    def test_fara_filtre_doar_cand_filtrul_a_golit(self):
        r = self.fa(ClientFals(interp())).intreaba("BCR?")["raspunsuri"][0]
        self.assertIsNone(r["fara_filtre"])                    # are valori
        r = self.fa(ClientFals(interp(banci=["brd"]))).intreaba("BRD?")["raspunsuri"][0]
        self.assertIsNone(r["fara_filtre"])                    # zero, dar fără filtre de golit

    def test_valorile_doar_text_numarate_separat(self):
        """Rezumatul are doar valorile cu cifră: fără numărul celorlalte, „1 valoare” stătea deasupra
        unui tabel cu mai multe rânduri (589 de valori doar text, neambigue, în mip_merge, 07.10.2026)."""
        self.randuri["bcr"] = [rand(5), rand(None), dict(rand(None), valoare_text="negociabil"),
                               rand(None, ambiguu=True)]
        r = self.fa(ClientFals(interp())).intreaba("BCR?")["raspunsuri"][0]
        self.assertEqual((r["total"], r["rezumat"][0]["n"], r["ambigue"], r["fara_cifra"]), (4, 1, 1, 2))

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
            (fara_init(anthropic.APITimeoutError), "40 s"),
            (fara_init(anthropic.APIConnectionError), "api.anthropic.com"),
            (fara_init(anthropic.InternalServerError, status_code=529), "529"),
        ]
        for exc, text in cazuri:
            with self.assertRaises(vox.EroareModel) as e:
                self.fa(ClientFals(exceptie=exc)).intreaba("BCR?")
            self.assertIn(text, str(e.exception))

    def test_jurnal(self):
        import anthropic
        self.fa(ClientFals(interp())).intreaba("BCR?")
        with self.assertRaises(vox.EroareModel):
            self.fa(ClientFals(exceptie=fara_init(anthropic.APIConnectionError))).intreaba("BRD?")
        fisiere = [f for f in os.listdir(self.dir) if f.endswith(".jsonl")]
        self.assertEqual(len(fisiere), 1)
        self.assertRegex(fisiere[0], r"^\d{4}-\d{2}\.jsonl$")
        with open(os.path.join(self.dir, fisiere[0]), encoding="utf-8") as f:
            randuri = [json.loads(x) for x in f]
        self.assertEqual([r["intrebare"] for r in randuri], ["BCR?", "BRD?"])
        self.assertEqual(randuri[0]["randuri"], {"bcr": 2})
        self.assertIn("api.anthropic.com", randuri[1]["eroare"])

    def test_jurnal_si_cand_cade_baza(self):
        """Apelul la model s-a plătit deja; dacă baza cade după el, întrebarea tot intră în jurnal."""
        def cauta(*a):
            raise RuntimeError("baza nu răspunde")
        q = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: None,
                               client=ClientFals(interp()), dir_jurnal=self.dir)
        with self.assertRaises(RuntimeError):
            q.intreaba("BCR?")
        with open(os.path.join(self.dir, os.listdir(self.dir)[0]), encoding="utf-8") as f:
            rand_jurnal = json.loads(f.readline())
        self.assertIn("baza nu răspunde", rand_jurnal["eroare"])
        self.assertEqual(rand_jurnal["tokeni"]["intrare"], 1200)

    def test_stare_si_token(self):
        q = self.fa(ClientFals(interp()))
        self.assertEqual(set(q.stare()), {"activ", "model"})
        self.assertGreaterEqual(len(q.token), 32)
        self.assertNotEqual(q.token, self.fa(ClientFals(interp())).token)

    def test_conversatie_noua_si_continuata(self):
        q = self.fa(ClientFals(interp()))
        d = q.intreaba("Cât costă administrarea contului la BCR?")
        c = d["conversatie"]
        self.assertTrue(vox.Istoric.valid(c))
        q._client = ClientFals(interp(banci=["brd"]))
        d2 = q.intreaba("și la BRD?", d["interpretare"], c)
        self.assertEqual(d2["conversatie"], c)
        conv = q.istoric.citeste(c)
        self.assertEqual([t["intrebare"] for t in conv["ture"]],
                         ["Cât costă administrarea contului la BCR?", "și la BRD?"])
        self.assertEqual(conv["ture"][1]["raspuns"]["raspunsuri"][0]["banca"], "brd")
        self.assertNotIn("conversatie", conv["ture"][1]["raspuns"])
        self.assertEqual(len(q.istoric.lista()), 1)

    def test_conversatie_stearsa_nu_se_plateste(self):
        """Ștearsă în alt tab sau id greșit: refuzul vine înainte de model, deci nimic plătit."""
        c = ClientFals(interp())
        q = self.fa(c)
        for rau in (q.istoric.id_nou(), "../x", 42, ""):
            with self.assertRaises(vox.Respins) as e:
                q.intreaba("și la BRD?", None, rau)
            self.assertEqual(str(e.exception), "Conversația nu mai există.")
        self.assertEqual(c.cereri, [])

    def test_eroarea_modelului_nu_intra_in_conversatie(self):
        import anthropic
        q = self.fa(ClientFals(exceptie=fara_init(anthropic.APIConnectionError)))
        with self.assertRaises(vox.EroareModel):
            q.intreaba("BCR?")
        self.assertEqual(q.istoric.lista(), [])

    def test_fara_disc_raspunsul_vine_oricum(self):
        q = self.fa(ClientFals(interp()))

        def cade(*a, **k):
            raise OSError("disc plin")
        q.istoric.adauga = cade
        d = q.intreaba("BCR?")
        self.assertEqual((d["conversatie"], d["raspunsuri"][0]["banca"]), (None, "bcr"))

    def test_jurnalul_leaga_intrebarea_de_conversatie(self):
        d = self.fa(ClientFals(interp())).intreaba("BCR?")
        (jurnal,) = [f for f in os.listdir(self.dir) if f.endswith(".jsonl")]
        with open(os.path.join(self.dir, jurnal), encoding="utf-8") as f:
            self.assertEqual(json.loads(f.readline())["conversatie"], d["conversatie"])


class CuvinteCautare(unittest.TestCase):
    def test_cuvinte_cautare(self):
        self.assertEqual(vox.cuvinte_cautare("Plată facturi"), ["plat", "factu"])
        self.assertEqual(vox.cuvinte_cautare("ȘTERGERE Ţară"), ["sterge", "tara"])
        # niciun wildcard LIKE (%, _) și niciun semn ajung în parametru
        self.assertEqual(vox.cuvinte_cautare("100% gratuit_x'; drop--"), ["100", "gratu", "drop"])
        self.assertEqual(vox.cuvinte_cautare("a de la card card"), ["card"])
        self.assertEqual(vox.cuvinte_cautare("unu doi trei patru cinci sase sapte"),
                         ["unu", "doi", "trei", "patr", "cinc"])

    def test_cifrele_nu_se_taie(self):
        """„100000” tăiat la „1000” ar potrivi orice sumă care conține 1000 (review, 06.10.2026)."""
        self.assertEqual(vox.cuvinte_cautare("plafon 100000 lei 2024"), ["plaf", "100000", "lei", "2024"])

    def test_flexiunea_romaneasca(self):
        """„datoria vamală” trebuie să găsească „datoriei vamale” (BCR, 13 valori): pe subșirul exact
        căutarea dădea 0 rânduri (măsurat pe mip, 06.10.2026)."""
        cuvinte = vox.cuvinte_cautare("datoria vamală")
        self.assertEqual(cuvinte, ["dator", "vama"])
        self.assertTrue(all(c in "decontarea electronica a datoriei vamale" for c in cuvinte))
        self.assertEqual(vox.cuvinte_cautare(None), [])
        self.assertEqual(vox.cuvinte_cautare(""), [])


class Http(unittest.TestCase):
    """Rutele din server, pe un port liber, cu un client fals în locul modelului."""

    @classmethod
    def setUpClass(cls):
        import server
        cls.server_mod = server
        cls.vechi = server.VOX
        cls.client = ClientFals(interp())
        server.VOX = vox.Vox(
            context=lambda: CTX, cauta=lambda *a: [rand(5)], stare_banca=lambda b: None,
            client=cls.client, dir_jurnal=tempfile.mkdtemp(prefix="vox_http_"))
        cls.srv = server.Server(("::", 0), server.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.env_vechi = {k: os.environ.get(k) for k in ("MIP_PERMITE_VOX", "ANTHROPIC_API_KEY",
                                                         "MCC_AUTH_LOCAL", "MCC_AUTH_OBLIGATORIE")}
        os.environ.pop("MCC_AUTH_OBLIGATORIE", None)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.server_mod.VOX = cls.vechi
        for k, v in cls.env_vechi.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def setUp(self):
        os.environ["MIP_PERMITE_VOX"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-" + "x" * 90
        # Vox merge pe laptop, unde autentificarea e scurtătura locală; poarta și rolurile au
        # testele lor în test_server_autentificare.py, aici doar că Vox stă în spatele ei
        os.environ["MCC_AUTH_LOCAL"] = "admin"

    def test_fara_sesiune_401_pe_toate_rutele(self):
        """Rutele Vox nu sunt în RUTE, deci la unirea cu autentificarea (07.10.2026) puteau rămâne
        înaintea porții: întrebarea plătită și istoricul, deschise oricui din rețea. Cu corp, un POST
        mai verifică și ordinea: citit înaintea porții, _goleste_corpul aștepta octeți care nu mai
        vin, iar cererea rămânea fără răspuns."""
        t = self.token()
        id_ = vox.Istoric.id_nou()
        os.environ["MCC_AUTH_LOCAL"] = ""
        n = len(self.client.cereri)
        cazuri = [("GET", "/api/vox", None), ("GET", "/api/vox/conversatii", None),
                  ("GET", f"/api/vox/conversatii/{id_}", None),
                  ("POST", "/api/vox", {"intrebare": "BCR?"}),
                  ("POST", f"/api/vox/conversatii/{id_}/redenumeste", {"titlu": "x"}),
                  ("POST", f"/api/vox/conversatii/{id_}/sterge", {})]
        for metoda, cale, corp in cazuri:
            self.assertEqual(self.cere(metoda, cale, corp, {"X-MIP-Token": t}),
                             (401, {"eroare": "neautentificat"}), (metoda, cale))
        self.assertEqual(len(self.client.cereri), n)   # niciun apel plătit

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
        return self.cere("GET", "/api/vox")[1]["token"]

    def test_get(self):
        cod, d = self.cere("GET", "/api/vox")
        self.assertEqual((cod, d["activ"], d["model"]), (200, True, "claude-haiku-4-5"))
        self.assertEqual(d["token"], self.server_mod.VOX.token)
        self.assertNotEqual(d["token"], self.server_mod.RULARI.token)

    def test_get_inactiv_fara_token(self):
        os.environ["ANTHROPIC_API_KEY"] = "placehold1"
        cod, d = self.cere("GET", "/api/vox")
        self.assertEqual((cod, d["activ"]), (200, False))
        self.assertNotIn("token", d)

    def test_get_host_strain(self):
        self.assertEqual(self.cere("GET", "/api/vox", host=f"evil.com:{self.port}")[0], 403)

    def test_post_merge_si_din_vite(self):
        """Din `npm run dev`, proxy-ul Vite rescrie Host-ul la server, dar Origin rămâne :5173."""
        t = self.token()
        for origine in (f"http://localhost:{self.port}", "http://localhost:5173", "http://127.0.0.1:5173"):
            cod, d = self.cere("POST", "/api/vox", {"intrebare": "BCR?"},
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
            cod, _ = self.cere("POST", "/api/vox", {"intrebare": "BCR?"}, antete, host)
            self.assertEqual(cod, 403, (antete, host))
        self.assertEqual(len(self.client.cereri), n)   # niciun apel plătit

    def test_refuzul_ajunge_ca_403_nu_ca_conexiune_intrerupta(self):
        """Un 403 trimis cu corpul necitit închidea socket-ul cu date în buffer; Windows răspundea cu
        RST, iar clientul vedea ConnectionAbortedError (3 din 25 de rulări ale testelor, 06.10.2026).
        În pagină, un token expirat ar fi apărut ca „serverul nu răspunde”."""
        for _ in range(1000):
            cod, _ = self.cere("POST", "/api/vox", {"intrebare": "x" * 3000}, {"X-MIP-Token": "gresit"})
            self.assertEqual(cod, 403)

    def test_post_inactiv(self):
        t = self.token()
        os.environ["MIP_PERMITE_VOX"] = "0"
        cod, d = self.cere("POST", "/api/vox", {"intrebare": "BCR?"}, {"X-MIP-Token": t})
        self.assertEqual(cod, 403)
        self.assertIn("MIP_PERMITE_VOX", d["eroare"])

    def test_post_forma(self):
        ok = {"X-MIP-Token": self.token()}
        self.assertEqual(self.cere("POST", "/api/vox", {"intrebare": ""}, ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/vox", {"intrebare": "a" * 501}, ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/vox", ["BCR?"], ok)[0], 400)
        self.assertEqual(self.cere("POST", "/api/vox", {"intrebare": "x" * 5000}, ok)[0], 400)
        cod, _ = self.cere("POST", "/api/vox", None, dict(ok, **{"Content-Type": "text/plain"}))
        self.assertEqual(cod, 415)

    def test_eroare_model_502(self):
        import anthropic
        ok = {"X-MIP-Token": self.token()}
        vechi = self.server_mod.VOX._client
        self.server_mod.VOX._client = ClientFals(exceptie=fara_init(anthropic.APIConnectionError))
        try:
            cod, d = self.cere("POST", "/api/vox", {"intrebare": "BCR?"}, ok)
        finally:
            self.server_mod.VOX._client = vechi
        self.assertEqual(cod, 502)
        self.assertIn("api.anthropic.com", d["eroare"])

    def test_post_salveaza_si_continua(self):
        ok = {"X-MIP-Token": self.token()}
        cod, d = self.cere("POST", "/api/vox", {"intrebare": "BCR?"}, ok)
        self.assertEqual(cod, 200)
        c = d["conversatie"]
        cod, d2 = self.cere("POST", "/api/vox",
                            {"intrebare": "și la BRD?", "anterior": d["interpretare"], "conversatie": c}, ok)
        self.assertEqual((cod, d2["conversatie"]), (200, c))
        self.assertEqual([t["intrebare"] for t in self.server_mod.VOX.istoric.citeste(c)["ture"]],
                         ["BCR?", "și la BRD?"])
        n = len(self.client.cereri)
        cod, d3 = self.cere("POST", "/api/vox", {"intrebare": "BCR?", "conversatie": "0" * 16}, ok)
        self.assertEqual((cod, d3["eroare"], len(self.client.cereri)), (400, "Conversația nu mai există.", n))

    def test_conversatii_lista_citire_redenumire_stergere(self):
        ok = {"X-MIP-Token": self.token()}
        c = self.cere("POST", "/api/vox", {"intrebare": "Cât costă administrarea contului la BCR?"}, ok)[1]["conversatie"]
        cod, lista = self.cere("GET", "/api/vox/conversatii")
        self.assertEqual(cod, 200)
        self.assertIn(c, [x["id"] for x in lista])
        cod, conv = self.cere("GET", f"/api/vox/conversatii/{c}")
        self.assertEqual((cod, conv["titlu"], len(conv["ture"])), (200, "Cât costă administrarea contului la BCR?", 1))
        cod, d = self.cere("POST", f"/api/vox/conversatii/{c}/redenumeste", {"titlu": "BCR, cont"}, ok)
        self.assertEqual((cod, d), (200, {"titlu": "BCR, cont", "redenumita": True}))
        cod, d = self.cere("POST", f"/api/vox/conversatii/{c}/redenumeste", {"titlu": "x" * 121}, ok)
        self.assertEqual((cod, d["eroare"]), (400, "Titlul are peste 120 de caractere."))
        cod, d = self.cere("POST", f"/api/vox/conversatii/{c}/sterge", {}, ok)
        self.assertEqual((cod, d), (200, {"sters": True}))
        self.assertEqual(self.cere("GET", f"/api/vox/conversatii/{c}")[0], 404)
        self.assertEqual(self.cere("POST", f"/api/vox/conversatii/{c}/sterge", {}, ok)[0], 404)
        self.assertEqual(self.cere("POST", f"/api/vox/conversatii/{c}/redenumeste", {"titlu": "y"}, ok)[0], 404)

    def test_conversatii_protejate(self):
        ok = {"X-MIP-Token": self.token()}
        c = self.cere("POST", "/api/vox", {"intrebare": "BCR?"}, ok)[1]["conversatie"]
        for antete, host in (({}, None), ({"X-MIP-Token": "gresit"}, None),
                             ({"X-MIP-Token": self.server_mod.RULARI.token}, None),
                             (dict(ok, Origin="http://evil.com"), None), (ok, f"evil.com:{self.port}")):
            for actiune, corp in (("sterge", {}), ("redenumeste", {"titlu": "x"})):
                cod, _ = self.cere("POST", f"/api/vox/conversatii/{c}/{actiune}", corp, antete, host)
                self.assertEqual(cod, 403, (antete, host, actiune))
        cod, _ = self.cere("POST", f"/api/vox/conversatii/{c}/sterge", None, dict(ok, **{"Content-Type": "text/plain"}))
        self.assertEqual(cod, 415)
        self.assertEqual(self.cere("GET", "/api/vox/conversatii", host=f"evil.com:{self.port}")[0], 403)
        self.assertEqual(self.cere("GET", f"/api/vox/conversatii/{c}", antete={"Origin": "http://evil.com"})[0], 403)
        self.assertEqual(self.cere("GET", f"/api/vox/conversatii/{c}")[0], 200)     # nimic șters

    def test_conversatii_id_invalid(self):
        ok = {"X-MIP-Token": self.token()}
        for cale in ("/api/vox/conversatii/..%2F..%2Fserver", "/api/vox/conversatii/../../app/server.py",
                     "/api/vox/conversatii/ABCDEF0123456789", "/api/vox/conversatii/"):
            self.assertEqual(self.cere("GET", cale)[0], 404, cale)
        self.assertEqual(self.cere("POST", "/api/vox/conversatii/../x/sterge", {}, ok)[0], 404)
        self.assertEqual(self.cere("POST", f"/api/vox/conversatii/{'0' * 16}/altceva", {}, ok)[0], 404)

    def test_conversatie_cu_litera_taiata_tot_se_listeaza(self):
        """Prin server: înainte, o literă tăiată închidea conexiunea, iar pagina arăta „serverul nu răspunde”."""
        ok = {"X-MIP-Token": self.token()}
        c = self.cere("POST", "/api/vox", {"intrebare": "BCR?"}, ok)[1]["conversatie"]
        with open(os.path.join(self.server_mod.VOX.istoric.dir, c + ".jsonl"), "ab") as f:
            f.write('{"intrebare": "Câ'.encode("utf-8")[:-1])
        cod, lista = self.cere("GET", "/api/vox/conversatii")
        self.assertEqual(cod, 200)
        self.assertIn(c, [x["id"] for x in lista])
        self.assertEqual(self.cere("GET", f"/api/vox/conversatii/{c}")[0], 200)

    def test_conversatii_eroare_neasteptata_raspunde_json(self):
        vechi = self.server_mod.VOX.istoric.lista
        self.server_mod.VOX.istoric.lista = lambda: 1 / 0
        try:
            cod, d = self.cere("GET", "/api/vox/conversatii")
        finally:
            self.server_mod.VOX.istoric.lista = vechi
        self.assertEqual((cod, d["eroare"]), (500, "ZeroDivisionError: division by zero"))

    def test_conversatii_si_cu_vox_oprit(self):
        """Lista doar citește fișiere locale: merge și fără cheie (istoricul rămâne de citit)."""
        os.environ["MIP_PERMITE_VOX"] = "0"
        self.assertEqual(self.cere("GET", "/api/vox/conversatii")[0], 200)

    def test_baza_oprita_503_cu_mesaj(self):
        """Cu Postgres oprit, pagina arăta textul brut psycopg2 („OperationalError: connection to server
        at …”), netradus; acum un mesaj fix, cu traducere, și la întrebare, și la încărcarea paginii."""
        import psycopg2

        def cade(*a, **k):
            raise psycopg2.OperationalError('connection to server at "localhost" (::1), port 5432 failed')
        ok = {"X-MIP-Token": self.token()}
        vechi_cauta, vechi_interogare = self.server_mod.VOX._cauta, self.server_mod.interoghează
        self.server_mod.VOX._cauta = cade
        self.server_mod.interoghează = cade
        try:
            raspunsuri = [self.cere("POST", "/api/vox", {"intrebare": "BCR?"}, ok), self.cere("GET", "/api/sumar")]
        finally:
            self.server_mod.VOX._cauta, self.server_mod.interoghează = vechi_cauta, vechi_interogare
        for cod, d in raspunsuri:
            self.assertEqual((cod, d["eroare"]), (503, "Baza de date nu răspunde (Postgres oprit sau MIP_DSN greșit)."))


class Preturi(unittest.TestCase):
    def test_modelele_de_ales_au_pret(self):
        """MIP_VOX_MODEL poate fi schimbat; fără preț, costul ar apărea „necunoscut”."""
        for m in ("claude-haiku-4-5", "claude-sonnet-5-5", "claude-opus-5-5"):
            self.assertIsNotNone(vox.preturi.cost(m, 1000, 100), m)
        self.assertAlmostEqual(vox.preturi.cost("claude-opus-5-5", 1_000_000, 0), 4.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
