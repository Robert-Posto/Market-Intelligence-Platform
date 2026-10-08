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
        {"camp": "dae", "n": 120, "unitati": ["procent"], "categorii": ["credite"],
         "exemple": ["DAE credit ipotecar"]},
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
    "clasabile": {"comisioane": ["administrare_cont"],
                  "dobanzi": {"dae": ["credite"], "nominala": ["conturi_carduri", "credite", "depozite"]}},
    "functii": [{"functie": "hce_contactless", "titlu": "Plată contactless direct din aplicație"},
                {"functie": "in_app_chat", "titlu": "Chat cu banca în aplicație"},
                {"functie": "ropay", "titlu": "RoPay (plăți instant din cont)"}],
    "aplicatii": [{"banca": "bcr", "aplicatie": "George Romania"}, {"banca": "brd", "aplicatie": "YOU BRD"},
                  {"banca": "brd", "aplicatie": "MyBRD Mobile"}, {"banca": "libra", "aplicatie": "Libra Bank"}],
}


def interp(**k):
    baza = {"tip": "cautare", "banci": ["bcr"], "concept": "administrare_cont", "categorie": None,
            "termen": None, "produs_credit": None, "text_cautat": None, "clarificare": None}
    baza.update(k)
    return baza


def apl(**k):
    """O interpretare de tip `aplicatii`, cu toate cheile din CHEI."""
    baza = dict(vox._gol("aplicatii"), banci=["bcr"], aspect="functii")
    baza.update(k)
    return baza


def rand(valoare, unitate="lei", scenariu="comision|x", ambiguu=False):
    return {"valoare": valoare, "unitate": unitate, "cod_scenariu": scenariu, "ambiguu": ambiguu}


class ClientFals:
    """Un client Anthropic fals: întoarce JSON-ul dat și ține minte cererile."""

    def __init__(self, raspuns=None, stop="end_turn", exceptie=None, scriere=0):
        self.cereri = []
        self._raspuns, self._stop, self._exceptie = raspuns, stop, exceptie
        self._scriere = scriere
        self.messages = self

    def create(self, **kw):
        self.cereri.append(kw)
        if self._exceptie:
            raise self._exceptie
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=json.dumps(self._raspuns))],
            stop_reason=self._stop,
            usage=types.SimpleNamespace(input_tokens=1200, output_tokens=60,
                                        cache_read_input_tokens=7000, cache_creation_input_tokens=self._scriere))


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
        self.assertEqual(p["concept"]["anyOf"][0]["enum"], ["administrare_cont", "nominala", "dae"])
        self.assertEqual(p["tip"]["enum"], list(vox.TIPURI))
        self.assertEqual(p["segment"]["anyOf"][0]["enum"], list(vox.ORDINE_SEGMENT))
        self.assertEqual(p["metrica"]["anyOf"][0]["enum"], list(vox.METRICI))
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
        # „Care bancă are cel mai mic comision?” era refuzată de 3 ori în octombrie: clasamentul are tipul lui
        self.assertIn("tip = clasament", text)
        self.assertIn("Clasabile: comisioane (în lei): administrare_cont; dobânzi (cu categoria): dae (credite)", text)
        self.assertNotIn("clasamente de tipul", text)
        # evaluarea din 07.10.2026 (36/40): comparațiile fără bancă numită ieșeau `neclar` („La care
        # bancă…?”), „comision de administrare” cerea „cont sau card?”, iar „pentru firme la BCR” cerea
        # „ce tip de cont pentru firme?”
        self.assertIn("e clasament chiar fără bancă numită", text)
        self.assertIn("„Comisionul de administrare” fără alt detaliu e `administrare_cont`", text)
        self.assertIn("nu fac întrebarea neclară", text)
        # a doua evaluare (36/40): „cel mai mic comision” ieșea `cea_mai_buna`, „unde stă Libra” fără
        # Libra, „pentru firme” cerea „PFA, IMM sau PJ?”, „datoria vamală” tot `neclar`: exemple explicite
        self.assertIn("concept = null, text_cautat = X", text)
        # a treia evaluare (39/40): „Unde stă Libra la DAE…?” ieșea căutare la Libra, nu clasament
        self.assertIn("„Unde stă Libra la …?”, „pe ce loc e Libra la …?” → clasament (nu căutare), banci = [libra]", text)
        self.assertIn("compară prețul obișnuit, deci metrica = null", text)
        self.assertIn("„Firme” e pj; nu cere clarificări despre segment", text)
        # la temperatura 0 (07.10.2026): „TrezoNet la BCR” ieșea `neclar` cu banci = [], deși clarificarea
        # numea BCR — cu banca păstrată, serverul o face căutare; „Care bancă… datoria vamală” tot `neclar`
        self.assertIn("La neclar completezi totuși ce ai înțeles", text)
        self.assertIn("sunt întotdeauna clasament", text)
        # revizia finală: „cine dă cea mai mare dobândă” ieșea `cea_mai_buna` (Vista 6,25% înaintea lui
        # Raiffeisen, contra medianei din spec), iar „care bancă… = clasament” putea trimite aplicațiile
        # pe „nu avem clasament” în loc de „în afara”
        self.assertIn("„cine dă cea mai mare dobândă…” compară prețul obișnuit", text)
        self.assertIn("cele despre aplicații („care bancă are cea mai bună aplicație?”) sunt aplicatii", text)
        # conversația din 08.10.2026: „Cât costă administrarea contului la BCR și la BRD?”, pusă după
        # „… pentru firme la BCR?”, păstra segmentul pj, deși nu-l spunea
        self.assertIn("e o întrebare nouă, nu o continuare: nu păstrezi nimic din cea anterioară", text)
        # identic la fiecare apel: cache-ul promptului cere un prefix stabil
        self.assertEqual(text, vox.prompt(CTX))


    def test_prompt_aplicatii(self):
        text = vox.prompt(CTX)
        self.assertIn("tip = aplicatii", text)
        self.assertIn("Funcțiile aplicațiilor (slug: titlu): hce_contactless: Plată contactless direct din aplicație; "
                      "in_app_chat: Chat cu banca în aplicație; ropay: RoPay (plăți instant din cont)", text)
        self.assertIn("Aplicațiile (bancă: nume): bcr: George Romania; brd: YOU BRD; brd: MyBRD Mobile; "
                      "libra: Libra Bank", text)
        self.assertIn("(„Apple Pay”) → functie = null și numele ei în text_cautat", text)
        self.assertIn("(„cu cel puțin 1.000 de note” → 1000)", text)
        self.assertIn("recenziile aplicațiilor, trackere, permisiuni, campanii", text)
        self.assertNotIn("(aplicații, recenzii, campanii", text)


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

    def test_clasament_bun_fara_banci(self):
        curat, _ = vox.valideaza(interp(tip="clasament", banci=[], segment="pj", metrica="cea_mai_buna"), CTX)
        self.assertEqual((curat["tip"], curat["banci"], curat["segment"], curat["metrica"]),
                         ("clasament", [], "pj", "cea_mai_buna"))

    def test_clasament_dobanda_categoria_implicita_sau_neclar(self):
        """`dae` e doar la credite; `nominala` e și depozit, și credit: fără categorie, un clasament ar
        amesteca 6,5% la depozit cu 9,9% la ipotecar."""
        curat, _ = vox.valideaza(interp(tip="clasament", banci=[], concept="dae"), CTX)
        self.assertEqual((curat["tip"], curat["categorie"]), ("clasament", "credite"))
        curat, _ = vox.valideaza(interp(tip="clasament", banci=[], concept="nominala"), CTX)
        self.assertEqual(curat["tip"], "neclar")

    def test_clasament_fara_concept_dar_cu_text_ramane_clasament(self):
        curat, _ = vox.valideaza(interp(tip="clasament", banci=[], concept=None, text_cautat="datoria vamală"), CTX)
        self.assertEqual(curat["tip"], "clasament")
        self.assertEqual(vox.valideaza(interp(tip="clasament", banci=[], concept=None), CTX)[0]["tip"], "neclar")

    def test_segment_si_metrica_necunoscute(self):
        for rau in (interp(segment="firme"), interp(metrica="maxim")):
            self.assertEqual(vox.valideaza(rau, CTX)[0]["tip"], "neclar", rau)

    def test_anterior_vechi_fara_campurile_noi(self):
        """O conversație salvată înainte de 07.10.2026 are interpretări fără `segment` și `metrica`."""
        vechi = {k: v for k, v in interp().items() if k not in ("segment", "metrica")}
        self.assertEqual(vox.verifica_anterior(vechi)["segment"], None)


class ValidareAplicatii(unittest.TestCase):
    """Tipul `aplicatii` (decizia lui Nicolae, 08.10.2026): funcțiile din analiza Android sau notele din magazine."""

    def test_schema_are_campurile_noi(self):
        s = vox.schema(CTX)
        p = s["properties"]
        self.assertIn("aplicatii", p["tip"]["enum"])
        self.assertEqual(p["functie"]["anyOf"][0]["enum"], ["hce_contactless", "in_app_chat", "ropay"])
        self.assertEqual(p["aspect"]["anyOf"][0]["enum"], ["functii", "note"])
        self.assertEqual(p["prag_note"], {"anyOf": [{"type": "integer"}, {"type": "null"}]})
        self.assertEqual(sorted(s["required"]), sorted(vox.CHEI))

    def test_functie_fara_banci(self):
        i, _ = vox.valideaza(apl(banci=[], functie="ropay", aspect=None), CTX)
        self.assertEqual((i["tip"], i["functie"], i["aspect"], i["banci"]), ("aplicatii", "ropay", "functii", []))

    def test_functia_inseamna_functii(self):
        i, _ = vox.valideaza(apl(functie="ropay", aspect="note", prag_note=100), CTX)
        self.assertEqual((i["aspect"], i["prag_note"]), ("functii", None))

    def test_aspect_implicit(self):
        self.assertEqual(vox.valideaza(apl(aspect=None), CTX)[0]["aspect"], "functii")
        i, _ = vox.valideaza(apl(banci=[], aspect=None, text_cautat="Apple Pay"), CTX)
        self.assertEqual((i["tip"], i["aspect"], i["text_cautat"]), ("aplicatii", "functii", "Apple Pay"))

    def test_fara_nimic_e_neclar(self):
        i, _ = vox.valideaza(apl(banci=[], aspect=None), CTX)
        self.assertEqual((i["tip"], i["clarificare"]), ("neclar", None))

    def test_note_cu_si_fara_banci(self):
        self.assertEqual(vox.valideaza(apl(banci=[], aspect="note"), CTX)[0]["tip"], "aplicatii")
        self.assertEqual(vox.valideaza(apl(banci=["libra"], aspect="note"), CTX)[0]["banci"], ["libra"])

    def test_prag_note(self):
        """Un prag scris de model sau adus de un client modificat: doar întreg între 1 și 100.000.000, altfel se
        ignoră; pragul rafinează întrebarea, nu-i schimbă sensul."""
        self.assertEqual(vox.valideaza(apl(aspect="note", prag_note=1000), CTX)[0]["prag_note"], 1000)
        for rau in (True, "1000", 99.5, 0, -5, 10 ** 12, [100]):
            i, _ = vox.valideaza(apl(aspect="note", prag_note=rau), CTX)
            self.assertEqual((i["tip"], i["prag_note"]), ("aplicatii", None), rau)

    def test_campurile_comisioanelor_se_golesc(self):
        i, _ = vox.valideaza(apl(concept="administrare_cont", segment="pj", metrica="cea_mai_buna",
                                 clarificare="?"), CTX)
        self.assertEqual((i["concept"], i["segment"], i["metrica"], i["clarificare"]), (None, None, None, None))

    def test_alte_tipuri_golesc_campurile_noi(self):
        i, _ = vox.valideaza(dict(interp(), functie="ropay", aspect="note", prag_note=100), CTX)
        self.assertEqual((i["tip"], i["functie"], i["aspect"], i["prag_note"]), ("cautare", None, None, None))

    def test_functie_necunoscuta_e_neclar(self):
        self.assertEqual(vox.valideaza(apl(functie="apple_pay"), CTX)[0]["tip"], "neclar")

    def test_trei_banci(self):
        i, ignorate = vox.valideaza(apl(banci=["bcr", "brd", "ing", "libra"]), CTX)
        self.assertEqual((i["banci"], ignorate), (["bcr", "brd", "ing"], ["libra"]))

    def test_interpretare_veche_fara_campurile_noi(self):
        """Conversațiile salvate înainte de 08.10.2026 n-au `functie`, `aspect`, `prag_note`."""
        vechi = interp(segment=None, metrica=None)
        curat = vox.verifica_anterior(vechi)
        self.assertEqual((curat["functie"], curat["aspect"], curat["prag_note"]), (None, None, None))
        self.assertEqual(vox.valideaza(curat, CTX)[0]["tip"], "cautare")


class Rezumat(unittest.TestCase):
    def test_pe_unitate_fara_ambigue(self):
        r = vox.rezuma([rand(0), rand(5), rand(15), rand(999, ambiguu=True), rand(2, "eur"), rand(None)])
        self.assertEqual(r[0], {"segment": None, "unitate": "lei", "categorie": "comision", "n": 3,
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

    def test_pe_segment_pf_primul_fara_dublari(self):
        """BCR · administrare cont: 302 PJ, 234 PFA și 33 PF într-un singur interval (mip_merge, 07.10.2026).
        Un rând fără segment are grupa lui, nu intră și la PF."""
        r = vox.rezuma([dict(rand(30), segment="pj"), dict(rand(5), segment="pf"), rand(7),
                        dict(rand(10), segment="pfa"), dict(rand(0), segment="pf")])
        self.assertEqual([(g["segment"], g["n"]) for g in r], [("pf", 2), ("pfa", 1), ("pj", 1), (None, 1)])
        self.assertEqual((r[0]["minim"], r[0]["maxim"], r[0]["gratuite"]), (0, 5, 1))

    def test_fara_segment_un_singur_bloc(self):
        """La dobânzi sursele nu spun segmentul: grupele rămân ca înainte, pe număr de valori."""
        r = vox.rezuma([rand(6.5, "procent", "depozite|12"), rand(7, "procent", "depozite|12"),
                        rand(9.9, "procent", "credite|ipotecar")])
        self.assertEqual([(g["segment"], g["categorie"], g["n"]) for g in r],
                         [(None, "depozite", 2), (None, "credite", 1)])

    def test_segmentul_cerut_primul(self):
        """„… pentru firme la BCR?” arată grupa PJ prima; celelalte rămân, în ordinea obișnuită."""
        r = vox.rezuma([dict(rand(5), segment="pf"), dict(rand(30), segment="pj"), rand(7)], primul="pj")
        self.assertEqual([g["segment"] for g in r], ["pj", "pf", None])

    def test_moneda_la_dobanzi(self):
        """Libra · depozit (mip_merge, 08.10.2026): 4,75% în lei, 1,95% în euro și 9 valori fără monedă
        stăteau într-un singur interval; acum un card pe monedă, lei primul, nespusă la final."""
        def d(v, valuta):
            return dict(rand(v, "procent", "depozite|x"), valuta=valuta)
        r = vox.rezuma([d(2.2, None), d(1.95, "EUR"), d(5.5, None), d(4.75, "LEI"), d(4.5, "RON")],
                       categorii_rate=("depozite", "credite", "conturi_carduri"))
        self.assertEqual([(g["moneda"], g["n"], g["minim"], g["maxim"]) for g in r],
                         [("lei", 2, 4.5, 4.75), ("eur", 1, 1.95, 1.95), (None, 2, 2.2, 5.5)])

    def test_moneda_toata_nespusa(self):
        """8.559 de rânduri curente n-au moneda în `valuta` (08.10.2026): un singur card, „monedă nespusă”."""
        r = vox.rezuma([rand(2.2, "procent", "depozite|x"), rand(5.5, "procent", "depozite|x")],
                       categorii_rate=("depozite",))
        self.assertEqual([(g["moneda"], g["n"]) for g in r], [(None, 2)])

    def test_moneda_nu_la_comisioane(self):
        """La comisioane unitatea e moneda prețului: „Administrarea contului (EURO): 20 Lei” are `valuta` EUR."""
        r = vox.rezuma([dict(rand(20), valuta="EUR"), dict(rand(5), valuta="LEI")], categorii_rate=("depozite",))
        self.assertEqual(len(r), 1)
        self.assertNotIn("moneda", r[0])

    def test_frecvente_cand_sunt_mai_multe(self):
        """BCR · administrare cont PF (mip_merge, 08.10.2026): 16 valori lunare 0–100 lei, 6 anuale 0–1.200 și
        11 fără frecvență dădeau un singur „0 – 1.200 lei”."""
        def f(v, frecventa):
            return dict(rand(v), frecventa=frecventa)
        r = vox.rezuma([f(20, "lunar"), f(100, "lunar"), f(240, "anual"), f(0, None), f(1200, "anual"),
                        f(5, "lunar")])
        self.assertEqual(r[0]["frecvente"], [
            {"frecventa": "lunar", "n": 3, "minim": 5, "maxim": 100},
            {"frecventa": "anual", "n": 2, "minim": 240, "maxim": 1200},
            {"frecventa": None, "n": 1, "minim": 0, "maxim": 0}])
        self.assertEqual((r[0]["minim"], r[0]["maxim"]), (0, 1200))

    def test_o_singura_frecventa_fara_camp(self):
        r = vox.rezuma([dict(rand(20), frecventa="lunar"), dict(rand(5), frecventa="lunar")])
        self.assertNotIn("frecvente", r[0])

    def test_frecventa_cu_si_fara_diacritice(self):
        """Garanti · retragere numerar (mip_merge, 08.10.2026): „pe tranzactie” (90 de valori) și „pe tranzacție”
        (86) dădeau două rânduri cu aceeași etichetă, `pe tranzacție · 4` de două ori. Rămâne prima grafie văzută."""
        def f(v, frecventa):
            return dict(rand(v), frecventa=frecventa)
        r = vox.rezuma([f(1, "pe tranzactie"), f(2, "pe tranzacție"), f(5, None)])
        self.assertEqual(r[0]["frecvente"], [
            {"frecventa": "pe tranzactie", "n": 2, "minim": 1, "maxim": 2},
            {"frecventa": None, "n": 1, "minim": 5, "maxim": 5}])
        # rândurile care diferă doar prin grafie sunt o singură frecvență, deci fără `frecvente`
        r = vox.rezuma([f(1, "pe operatiune"), f(2, "pe operațiune")])
        self.assertNotIn("frecvente", r[0])

    def test_separa_tipurile(self):
        """Garanti · schimbarea PIN-ului: toate cele 7 valori neambigue sunt limite contactless (08.10.2026)."""
        limita = rand(100, "lei", "limita|x")
        pret, alte = vox.separa([rand(5), limita, rand(6.5, "procent", "depozite|12"), rand(1, "lei", "nota|y")],
                                ("depozite",))
        self.assertEqual([vox._categorie(x) for x in pret], ["comision", "depozite"])
        self.assertEqual([x["tip_alt"] for x in alte], ["limita", "nota"])
        self.assertIs(alte[0], limita)              # același rând: tabelul fișei îl arată cu eticheta


class Clasa(unittest.TestCase):
    NUME = {"bcr": "BCR", "brd": "BRD", "ing": "ING Bank", "libra": "Libra Internet Bank"}

    def celula(self, banca, valoare, minim=None, maxim=None):
        return {"banca": banca, "camp": "x", "n": 3, "valoare": valoare,
                "minim": valoare if minim is None else minim, "maxim": valoare if maxim is None else maxim,
                "serviciu": f"serviciu {banca}", "frecventa": "lunar", "conditie": None, "segment_necunoscut": False}

    def test_comision_crescator_depozit_descrescator(self):
        c = [self.celula("bcr", 8.5), self.celula("brd", 3), self.celula("ing", 5)]
        self.assertEqual([r["banca"] for r in vox.clasa(c, "mic_bun", "mediana", set(), self.NUME)], ["brd", "ing", "bcr"])
        self.assertEqual([r["banca"] for r in vox.clasa(c, "mare_bun", "mediana", set(), self.NUME)], ["bcr", "ing", "brd"])

    def test_egalitati_loc_comun(self):
        """La administrarea contului PF, 7 din 14 bănci au mediana 0 lei (mip_merge, 07.10.2026):
        „Libra pe locul 4” ar fi un loc arbitrar."""
        r = vox.clasa([self.celula("libra", 0), self.celula("bcr", 8.5), self.celula("brd", 0)],
                      "mic_bun", "mediana", {"libra"}, self.NUME)
        self.assertEqual([(x["banca"], x["loc"], x["loc_pana"], x["evidentiata"]) for x in r],
                         [("brd", 1, 2, False), ("libra", 1, 2, True), ("bcr", 3, 3, False)])

    def test_cea_mai_buna_varianta(self):
        c = [self.celula("bcr", 8.5, minim=0, maxim=35), self.celula("brd", 3, minim=1, maxim=5)]
        r = vox.clasa(c, "mic_bun", "cea_mai_buna", set(), self.NUME)
        self.assertEqual([(x["banca"], x["valoare"], x["serviciu"]) for x in r], [("bcr", 0, None), ("brd", 1, None)])
        r = vox.clasa(c, "mare_bun", "cea_mai_buna", set(), self.NUME)
        self.assertEqual([(x["banca"], x["valoare"]) for x in r], [("bcr", 35), ("brd", 5)])

    def test_alte_monede_trec_in_rand(self):
        c = [dict(self.celula("raiffeisen", 2.25), alte_monede={"n": 2, "din": 2}), self.celula("brd", 3)]
        r = {x["banca"]: x for x in vox.clasa(c, "mare_bun", "mediana", set(), self.NUME)}
        self.assertEqual(r["raiffeisen"]["alte_monede"], {"n": 2, "din": 2})
        self.assertNotIn("alte_monede", r["brd"])


def nota(banca, valoare, evaluari, **k):
    return {"banca": banca, "nota": valoare, "evaluari": evaluari, **k}


NUME = {"bcr": "BCR", "brd": "BRD — Groupe Société Générale", "ing": "ING Bank", "libra": "Libra Internet Bank",
        "procredit": "ProCredit Bank", "revolut": "Revolut"}


class Note(unittest.TestCase):
    """Clasamentul notelor (decizia lui Nicolae, 08.10.2026): fără prag, loc comun la aceeași notă cu o zecimală."""

    def test_loc_comun_in_ordinea_numelui(self):
        """BRD 4,83, BCR 4,81 și ING 4,79 au toate 4,8 în Google Play (06.10.2026): locurile 1–3, după nume."""
        c = vox.clasa_note([nota("ing", 4.79, 182106), nota("brd", 4.83, 234221), nota("bcr", 4.81, 155826),
                            nota("libra", 4.59, 3083)], {"libra"}, NUME)
        self.assertEqual([(r["banca"], r["loc"], r["loc_pana"], r["nota_afisata"]) for r in c["randuri"]],
                         [("bcr", 1, 3, 4.8), ("brd", 1, 3, 4.8), ("ing", 1, 3, 4.8), ("libra", 4, 4, 4.6)])
        self.assertEqual([r["evidentiata"] for r in c["randuri"]], [False, False, False, True])
        self.assertEqual((c["sub_prag"], c["fara_nota"]), ([], []))

    def test_rotunjire_in_sus_de_la_cinci(self):
        """`round(4.25, 1)` dă 4,2 (rotunjire la par); magazinul arată 4,3. TBI are 4,65 în Google Play: 4,7."""
        c = vox.clasa_note([nota("ing", 4.25, 10), nota("bcr", 4.65, 10)], set(), NUME)
        self.assertEqual([(r["banca"], r["nota_afisata"]) for r in c["randuri"]], [("bcr", 4.7), ("ing", 4.3)])

    def test_fara_prag_toate_clasate(self):
        """În App Store, ProCredit e pe locul 1 cu 5,0 din 6 note (24.09.2026): fără prag, rămâne acolo."""
        c = vox.clasa_note([nota("procredit", 5.0, 6), nota("revolut", 4.91, 332368)], set(), NUME)
        self.assertEqual([(r["banca"], r["loc"]) for r in c["randuri"]], [("procredit", 1), ("revolut", 2)])

    def test_cu_prag_sub_prag_separat(self):
        c = vox.clasa_note([nota("procredit", 5.0, 6), nota("revolut", 4.91, 332368), nota("libra", 4.47, 971)],
                           {"libra"}, NUME, prag=1000)
        self.assertEqual([(r["banca"], r["loc"]) for r in c["randuri"]], [("revolut", 1)])
        self.assertEqual([(r["banca"], r["evidentiata"]) for r in c["sub_prag"]],
                         [("libra", True), ("procredit", False)])
        self.assertNotIn("loc", c["sub_prag"][0])

    def test_fara_nota_la_final(self):
        c = vox.clasa_note([nota("bcr", None, 0), nota("ing", 4.0, 5)], set(), NUME)
        self.assertEqual([r["banca"] for r in c["randuri"]], ["ing"])
        self.assertEqual([(r["banca"], r["nota_afisata"]) for r in c["fara_nota"]], [("bcr", None)])

    def test_putine_note(self):
        play = vox.clasa_note([nota("bcr", 4.81, 155826), nota("procredit", 2.5, 16)], set(), NUME)
        ios = vox.clasa_note([nota("procredit", 5.0, 6), nota("ing", 4.85, 125858), nota("brd", 4.0, 4)], set(), NUME)
        self.assertEqual(vox.putine_note({"play": play, "app_store": ios}),
                         {"app_store": 2, "play": 1, "prag": 100,
                          "primul": {"magazin": "app_store", "banca": "procredit", "loc": 1, "loc_pana": 1, "evaluari": 6}})

    def test_putine_note_nimic_sau_fara_magazin(self):
        play = vox.clasa_note([nota("bcr", 4.81, 155826)], set(), NUME)
        self.assertIsNone(vox.putine_note({"play": play, "app_store": None}))


def coloana(banca, **verdicte):
    return {"banca": banca, "fara_aplicatie": False,
            "functii": {f: {"verdict": v, "surse": [], "dovada_text": None} for f, v in verdicte.items()}}


class Diferente(unittest.TestCase):
    """Diferențele pe două niveluri (decizia lui Nicolae, 08.10.2026)."""

    def test_bt_pay_si_libra(self):
        """BT Pay vs Libra (mip_merge, 08.10.2026): RoPay sigură; chatul, marketingul și asistentul vocal, probabile;
        Huawei și Google Wallet le au amândouă („sigur” / „probabil”), deci nu sunt diferențe."""
        bt = coloana("banca-transilvania", ropay="sigur", in_app_chat="probabil", marketing="probabil",
                     voice="absent", huawei="probabil", wallet_provisioning="sigur")
        libra = coloana("libra", ropay="absent", in_app_chat="absent", marketing="absent",
                        voice="probabil", huawei="sigur", wallet_provisioning="probabil")
        self.assertEqual([(x["functie"], x["nivel"], x["au"], x["n_au"]) for x in vox.diferente([bt, libra])],
                         [("in_app_chat", "probabil", ["banca-transilvania"], ["libra"]),
                          ("marketing", "probabil", ["banca-transilvania"], ["libra"]),
                          ("ropay", "sigur", ["banca-transilvania"], ["libra"]),
                          ("voice", "probabil", ["libra"], ["banca-transilvania"])])

    def test_neconcludent_nu_intra(self):
        self.assertEqual(vox.diferente([coloana("bcr", ropay="sigur"), coloana("brci", ropay="neconcludent")]), [])

    def test_trei_aplicatii_nivel_dupa_cea_sigura(self):
        d = vox.diferente([coloana("bcr", ropay="probabil"), coloana("brd", ropay="sigur"),
                           coloana("libra", ropay="absent")])
        self.assertEqual(d, [{"functie": "ropay", "nivel": "sigur", "au": ["bcr", "brd"], "n_au": ["libra"]}])

    def test_banca_fara_aplicatie_nu_intra(self):
        d = vox.diferente([coloana("bcr", ropay="sigur"), {"banca": "pko", "fara_aplicatie": True, "functii": {}}])
        self.assertEqual(d, [])


class Butoane(unittest.TestCase):
    """Butoanele de sub un răspuns (decizia lui Nicolae, 08.10.2026): fără model, deci gratuite."""

    def rasp(self, *segmente):
        return [{"rezumat": [{"segment": s} for s in segmente]}]

    def test_cautare_comision_cu_segmente(self):
        self.assertEqual(vox.butoane(interp(), self.rasp("pf", None), None), ["firme", "libra"])
        self.assertEqual(vox.butoane(interp(segment="pj"), self.rasp("pj"), None), ["pf", "libra"])
        self.assertEqual(vox.butoane(interp(segment="pfa"), self.rasp("pfa"), None), ["firme", "pf", "libra"])

    def test_fara_segment_in_rezumat_doar_libra(self):
        self.assertEqual(vox.butoane(interp(), self.rasp(None), None), ["libra"])

    def test_dobanzi_fara_segment(self):
        """Rândurile de dobânzi n-au segment în sursă: „Pentru firme” n-ar schimba nimic."""
        self.assertEqual(vox.butoane(interp(concept="nominala", categorie="depozite"), self.rasp("pf"), None),
                         ["libra"])

    def test_libra_deja_sau_trei_banci(self):
        self.assertEqual(vox.butoane(interp(banci=["libra"]), self.rasp(None), None), [])
        self.assertEqual(vox.butoane(interp(banci=["bcr", "brd", "ing"]), self.rasp(None), None), [])

    def test_clasament(self):
        i = interp(tip="clasament", banci=[])
        self.assertEqual(vox.butoane(i, [], {"sursa": "matrice"}), ["firme"])
        self.assertEqual(vox.butoane(dict(i, segment="pj"), [], {"sursa": "matrice"}), ["pf"])
        self.assertEqual(vox.butoane(dict(i, concept="nominala", categorie="depozite"), [], {"sursa": "rate"}), [])
        self.assertEqual(vox.butoane(i, [], {"concept": None, "neclasabil": True}), [])

    def test_neclar_in_afara(self):
        for tip in ("neclar", "in_afara"):
            self.assertEqual(vox.butoane(interp(tip=tip), [], None), [])

    def test_din_buton(self):
        self.assertEqual(vox.din_buton(interp(), "firme")["segment"], "pj")
        self.assertEqual(vox.din_buton(interp(segment="pj"), "pf")["segment"], "pf")
        self.assertEqual(vox.din_buton(interp(), "libra")["banci"], ["bcr", "libra"])
        self.assertEqual(vox.din_buton(interp(tip="clasament", banci=[]), "firme")["tip"], "clasament")

    def test_din_buton_refuza(self):
        # corpul JSON poate aduce în `buton` o listă, un obiect, null sau un număr: Respins (400), nu TypeError (500)
        for i, b in ((interp(), "toate"), (interp(concept="nominala", categorie="depozite"), "firme"),
                     (interp(tip="clasament", banci=[]), "libra"), (interp(banci=["libra"]), "libra"),
                     (interp(banci=["bcr", "brd", "ing"]), "libra"), (interp(tip="neclar"), "firme"),
                     (interp(), ["libra"]), (interp(), {"x": 1}), (interp(), None), (interp(), 5)):
            with self.assertRaises(vox.Respins, msg=(i, b)):
                vox.din_buton(i, b)


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

    def fa(self, client, stare_banca=lambda b: None, clasament=None, stare_banci=lambda: {}):
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((banca, concept, categorie, termen, produs, text))
            return self.randuri.get(banca, [])
        return vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=stare_banca,
                       clasament=clasament, stare_banci=stare_banci, client=client, dir_jurnal=self.dir)

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
        # cache de o oră: în conversația din 08.10.2026 (18 întrebări, 7,5 cenți), promptul s-a scris în cache
        # de 3 ori, la prima întrebare și după două pauze, de 9 și de 5 minute: 4,9 cenți
        self.assertEqual(cerere["system"][0]["cache_control"], {"type": "ephemeral", "ttl": "1h"})
        # patru evaluări cu aceleași 40 de întrebări au dat 36, 36, 39 și 37, cu alte greșeli de fiecare
        # dată (07.10.2026): la temperatura implicită aceeași întrebare putea fi înțeleasă altfel
        # SDK-ul 1.x a scos `temperature` din semnătură (TypeError), dar Haiku 4.5 îl acceptă
        self.assertEqual(cerere["extra_body"], {"temperature": 0})
        self.assertEqual(cerere["messages"],
                         [{"role": "user", "content": "Cât costă administrarea contului la BCR?"}])

    def test_scrierea_in_cache_de_o_ora(self):
        """Scrierea de o oră costă de 2 ori prețul de intrare, nu de 1,25 ori (documentația Anthropic)."""
        d = self.fa(ClientFals(interp(), scriere=12000)).intreaba("BCR?")
        self.assertAlmostEqual(d["cost_usd"], (1200 * 1 + 60 * 5 + 7000 * 0.1 + 12000 * 2) / 1e6)

    def test_temperatura_doar_la_haiku(self):
        """Opus 4.7 și modelele mai noi întorc 400 la orice `temperature`: un model schimbat din
        MIP_VOX_MODEL nu-l primește."""
        os.environ["MIP_VOX_MODEL"] = "claude-sonnet-5-5"
        try:
            c = ClientFals(interp())
            self.fa(c).intreaba("BCR?")
        finally:
            os.environ.pop("MIP_VOX_MODEL", None)
        self.assertNotIn("extra_body", c.cereri[0])

    def test_cautare_dupa_text(self):
        self.fa(ClientFals(interp(concept=None, text_cautat="datoria vamală"))).intreaba("vama la BCR?")
        self.assertEqual(self.cautari, [("bcr", None, None, None, None, "datoria vamală")])

    def test_fisa_doar_limite(self):
        """Garanti · schimbarea PIN-ului: niciun comision, doar limite; rezumatul gol, limitele în `alte`."""
        self.randuri["bcr"] = [rand(100, "lei", "limita|x"), rand(700, "lei", "limita|x")]
        r = self.fa(ClientFals(interp())).intreaba("PIN la BCR?")["raspunsuri"][0]
        self.assertEqual(r["rezumat"], [])
        self.assertEqual([(g["categorie"], g["n"], g["minim"], g["maxim"]) for g in r["alte"]],
                         [("limita", 2, 100, 700)])
        self.assertEqual([v.get("tip_alt") for v in r["randuri"]], ["limita", "limita"])

    def test_fisa_dobanzi_pe_moneda(self):
        self.randuri["bcr"] = [dict(rand(4.75, "procent", "depozite|12"), valuta="LEI"),
                               dict(rand(1.95, "procent", "depozite|12"), valuta="EUR")]
        r = self.fa(ClientFals(interp(concept="nominala", categorie="depozite"))).intreaba("depozit BCR?")
        rb = r["raspunsuri"][0]
        self.assertEqual([g["moneda"] for g in rb["rezumat"]], ["lei", "eur"])
        self.assertEqual(rb["alte"], [])

    def test_intrebarea_are_butoane(self):
        self.randuri["bcr"] = [dict(rand(5), segment="pf")]
        self.assertEqual(self.fa(ClientFals(interp())).intreaba("BCR?")["butoane"], ["firme", "libra"])

    def test_continua_fara_model(self):
        """„Pentru firme” sub „Cât costă administrarea contului la BCR?”: același drum ca o întrebare, fără model."""
        self.randuri["bcr"] = [dict(rand(5), segment="pf"), dict(rand(20), segment="pj")]
        c = ClientFals(interp())
        v = self.fa(c)
        d = v.continua(interp(), "firme")
        self.assertEqual(c.cereri, [])
        self.assertEqual((d["model"], d["cost_usd"], d["buton"]), (None, 0.0, "firme"))
        self.assertEqual(d["interpretare"]["segment"], "pj")
        self.assertEqual([g["segment"] for g in d["raspunsuri"][0]["rezumat"]], ["pj", "pf"])
        self.assertEqual(d["butoane"], ["pf", "libra"])
        tura = v.istoric.citeste(d["conversatie"])["ture"][0]
        self.assertEqual((tura["intrebare"], tura["raspuns"]["buton"]), ("Pentru firme", "firme"))

    def test_continua_refuza(self):
        v = self.fa(ClientFals(interp()))
        with self.assertRaises(vox.Respins):
            v.continua(None, "firme")                               # fără răspunsul de sub buton
        with self.assertRaises(vox.Respins):
            v.continua(interp(), "firme", "0" * 16)                 # conversație ștearsă
        with self.assertRaises(vox.Respins):
            v.continua(interp(banci=["libra"]), "libra")            # Libra e deja acolo
        with self.assertRaises(vox.Respins):
            v.continua(dict(interp(), concept=[]), "firme")         # corpul JSON poate aduce o listă: 400, nu 500
        with self.assertRaises(vox.Respins):
            v.continua(dict(interp(), banci=[["bcr"]]), "firme")    # la fel într-o listă de bănci

    def test_anterior_ajunge_la_model(self):
        c = ClientFals(interp(banci=["brd"]))
        self.fa(c).intreaba("și la BRD?", interp())
        continut = c.cereri[0]["messages"][0]["content"]
        self.assertIn('"concept": "administrare_cont"', continut)
        self.assertIn("și la BRD?", continut)

    def test_zero_valori_spune_de_ce(self):
        lipsa = {"stare": "blocata", "surse": 1, "robots": 0, "refuzate": 1, "pdf": 0}
        r = self.fa(ClientFals(interp(banci=["brd"])), stare_banca=lambda b: lipsa).intreaba("BRD?")["raspunsuri"][0]
        self.assertEqual((r["total"], r["stare_banca"], r["blocaje"]),
                         (0, "blocata", {"surse": 1, "robots": 0, "refuzate": 1, "pdf": 0}))

    def test_zero_cu_termen_spune_cate_sunt_fara(self):
        """Nici pe „termen nespecificat” nu iese nimic: fișa spune câte sunt fără niciun filtru, ca
        „nu avem valori” să nu se citească „banca n-are depozite”."""
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append(termen)
            return [] if termen else [rand(3.5, "procent", "depozite"), rand(3.6, "procent", "depozite")]
        c = ClientFals(interp(banci=["ing"], concept="nominala", categorie="depozite", termen="12"))
        q = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: None,
                    client=c, dir_jurnal=self.dir)
        r = q.intreaba("ING, depozit pe 12 luni?")["raspunsuri"][0]
        self.assertEqual((r["total"], r["fara_filtre"], r["filtre_relaxate"], self.cautari),
                         (0, 2, [], ["12", "necunoscut", None]))

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

    def test_pf_primele_inainte_de_taiere(self):
        """La BCR · administrare cont primele 50 de rânduri erau 18 PF, 19 PFA și 13 PJ amestecate
        (mip_merge, 07.10.2026): PF vin acum primele, apoi PFA, IMM, PJ și cele fără segment."""
        self.randuri["bcr"] = ([dict(rand(i), segment="pj") for i in range(30)] + [rand(7)]
                               + [dict(rand(i), segment="pfa") for i in range(30)]
                               + [dict(rand(1), segment="pf")] * 3)
        r = self.fa(ClientFals(interp())).intreaba("BCR?")["raspunsuri"][0]
        segmente = [x.get("segment") for x in r["randuri"]]
        self.assertEqual((r["total"], len(segmente)), (64, 50))
        self.assertEqual(segmente[:4], ["pf", "pf", "pf", "pfa"])
        self.assertEqual(segmente[-1], "pj")       # cel fără segment vine după PJ, dincolo de 50
        self.assertEqual([g["segment"] for g in r["rezumat"]], ["pf", "pfa", "pj", None])

    def test_termen_cade_pe_necunoscut(self):
        """Libra avea 11 dobânzi la depozite fără termen în sursă și niciuna pe 7–12 luni, iar fișa spunea
        „nu avem valori” (mip_merge, 07.10.2026). Interpretarea rămâne a omului, ca „și pe 6 luni?” să
        continue de la ce a cerut el."""
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((termen, produs))
            return [rand(4.75, "procent", "depozite")] * 11 if termen == "necunoscut" else []
        c = ClientFals(interp(banci=["libra"], concept="nominala", categorie="depozite", termen="12"))
        d = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: self.fail("banca are valori"),
                    client=c, dir_jurnal=self.dir).intreaba("Libra, depozit pe 12 luni?")
        r = d["raspunsuri"][0]
        self.assertEqual(self.cautari, [("12", None), ("necunoscut", None)])
        self.assertEqual((r["total"], r["filtre_relaxate"], r["fara_filtre"], r["blocaje"]),
                         (11, ["termen"], None, None))
        self.assertEqual(d["interpretare"]["termen"], "12")

    def test_produs_cade_pe_altele(self):
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((termen, produs))
            return [rand(8.1, "procent", "credite")] if produs == "altele" else []
        c = ClientFals(interp(banci=["bcr"], concept="nominala", categorie="credite", produs_credit="ipotecar"))
        r = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: None,
                    client=c, dir_jurnal=self.dir).intreaba("BCR, ipotecar?")["raspunsuri"][0]
        self.assertEqual(self.cautari, [(None, "ipotecar"), (None, "altele")])
        self.assertEqual((r["total"], r["filtre_relaxate"]), (1, ["produs"]))

    def test_termen_si_produs_cad_pe_rand(self):
        def cauta(banca, concept, categorie, termen, produs, text):
            self.cautari.append((termen, produs))
            return [rand(9.2, "procent", "credite")] if (termen, produs) == ("necunoscut", "altele") else []
        c = ClientFals(interp(banci=["bcr"], concept="nominala", categorie="credite", termen="lung",
                              produs_credit="ipotecar"))
        r = vox.Vox(context=lambda: CTX, cauta=cauta, stare_banca=lambda b: None,
                    client=c, dir_jurnal=self.dir).intreaba("BCR, ipotecar pe 30 de ani?")["raspunsuri"][0]
        self.assertEqual(self.cautari,
                         [("lung", "ipotecar"), ("necunoscut", "ipotecar"), ("necunoscut", "altele")])
        self.assertEqual((r["total"], r["filtre_relaxate"]), (1, ["termen", "produs"]))

    def test_blocaje_doar_cand_banca_n_are_valori(self):
        """ING: 48 de PDF-uri interzise de robots.txt din 158 de surse, deci nu „toate blocate”: fișa
        spunea doar „nu avem valori” (mip_merge, 07.10.2026)."""
        lipsa = {"stare": None, "surse": 158, "robots": 48, "refuzate": 0, "pdf": 48}
        r = self.fa(ClientFals(interp(banci=["ing"])), stare_banca=lambda b: lipsa).intreaba("ING?")["raspunsuri"][0]
        self.assertEqual((r["stare_banca"], r["blocaje"]),
                         (None, {"surse": 158, "robots": 48, "refuzate": 0, "pdf": 48}))
        r = self.fa(ClientFals(interp()), stare_banca=lambda b: self.fail("BCR are valori")).intreaba("BCR?")["raspunsuri"][0]
        self.assertIsNone(r["blocaje"])

    def celule_clasament(self, *args):
        self.cautari.append(args)
        cel = lambda b, v: {"banca": b, "camp": "administrare_cont", "n": 2, "valoare": v, "minim": v, "maxim": v,
                            "serviciu": None, "frecventa": None, "conditie": None, "segment_necunoscut": False}
        return {"sursa": "matrice", "grup": "cont_curent", "unitate": "lei", "sens": "mic_bun", "segment": "pf",
                "blocuri": [{"tip": "exact", "termen": "", "produs": "", "celule": [cel("bcr", 8.5), cel("libra", 0)]}]}

    def test_clasament(self):
        stari = {"brd": {"stare": "blocata", "surse": 1, "robots": 0, "refuzate": 1, "pdf": 0}}
        d = self.fa(ClientFals(interp(tip="clasament", banci=[])), clasament=self.celule_clasament,
                    stare_banci=lambda: stari).intreaba("Care bancă are cel mai mic comision de administrare?")
        c = d["clasament"]
        self.assertEqual((d["raspunsuri"], c["metrica"], c["segment"], c["libra"]),
                         ([], "mediana", "pf", {"loc": 1, "loc_pana": 1, "din": 2, "bloc": "exact"}))
        self.assertEqual([(r["banca"], r["loc"]) for r in c["blocuri"][0]["randuri"]], [("libra", 1), ("bcr", 2)])
        self.assertEqual([f["banca"] for f in c["fara_date"]], ["brd", "ing"])
        self.assertEqual(c["fara_date"][0]["stare"], "blocata")
        self.assertEqual(self.cautari, [("administrare_cont", None, None, None, None)])

    def test_clasament_libra_in_blocul_nespecificat(self):
        """Pe depozitul de 12 luni Libra n-are termenul scris în sursă: e pe locul 7 din 9 în blocul
        „nespecificat”, iar fișa spunea „Libra n-are valori aici” (revizia finală, mip_merge, 07.10.2026)."""
        cel = lambda b, v: {"banca": b, "camp": "nominala", "n": 2, "valoare": v, "minim": v, "maxim": v,
                            "serviciu": None, "frecventa": None, "conditie": None}

        def clasament(*a):
            return {"sursa": "rate", "grup": "depozite", "unitate": "procent", "sens": "mare_bun", "segment": None,
                    "blocuri": [{"tip": "exact", "termen": "12", "produs": "", "celule": [cel("bcr", 2.8)]},
                                {"tip": "nespecificat", "termen": "necunoscut", "produs": "",
                                 "celule": [cel("brd", 3), cel("libra", 2.25)]}]}
        d = self.fa(ClientFals(interp(tip="clasament", banci=[], concept="nominala", categorie="depozite", termen="12")),
                    clasament=clasament).intreaba("Cine dă cea mai mare dobândă la depozitul pe 12 luni?")
        self.assertEqual(d["clasament"]["libra"], {"loc": 2, "loc_pana": 2, "din": 2, "bloc": "nespecificat"})

    def test_clasament_neclasabil(self):
        d = self.fa(ClientFals(interp(tip="clasament", banci=[], concept=None, text_cautat="datoria vamală")),
                    clasament=lambda *a: None).intreaba("Cine are cel mai mic comision la vamă?")
        self.assertEqual(d["clasament"], {"concept": None, "text": "datoria vamală", "neclasabil": True})

    def test_cautare_fara_clasament(self):
        self.assertIsNone(self.fa(ClientFals(interp())).intreaba("BCR?")["clasament"])

    def test_cautare_segmentul_cerut_primul(self):
        self.randuri["bcr"] = [dict(rand(1), segment="pf"), dict(rand(2), segment="pj")]
        r = self.fa(ClientFals(interp(segment="pj"))).intreaba("BCR, firme?")["raspunsuri"][0]
        self.assertEqual([x["segment"] for x in r["randuri"]], ["pj", "pf"])
        self.assertEqual([g["segment"] for g in r["rezumat"]], ["pj", "pf"])


class StareBanca(unittest.TestCase):
    """`_stare_banca_vox` din server: ce spune fișa când banca n-are valori."""

    def setUp(self):
        import server
        self.server, self.vechi, self.cereri = server, server.interoghează, []

    def tearDown(self):
        self.server.interoghează = self.vechi

    def stare(self, numere):
        self.server.interoghează = lambda sql, params=None: self.cereri.append((sql, params)) or [{"slug": "ing", **numere}]
        return self.server._stare_banca_vox("ing")

    def test_blocaje_partiale_pe_motiv(self):
        s = self.stare({"surse": 158, "blocate": 48, "robots": 48, "pdf": 48})
        self.assertEqual(s, {"stare": None, "surse": 158, "robots": 48, "refuzate": 0, "pdf": 48})
        sql, params = self.cereri[0]
        self.assertEqual(params, ("ing",))
        self.assertIn("LIKE 'ROBOTS%%'", sql)   # un singur % strică o interogare cu parametri (psycopg2)

    def test_toate_blocate_si_fara_surse(self):
        s = self.stare({"surse": 1, "blocate": 1, "robots": 0, "pdf": 0})
        self.assertEqual((s["stare"], s["refuzate"]), ("blocata", 1))
        self.assertEqual(self.stare({"surse": 0, "blocate": 0, "robots": 0, "pdf": 0})["stare"], "fara_surse")


class CititoriClasament(unittest.TestCase):
    """Cititorii din server pentru clasamente: sursa celulelor, blocurile, motivul pe toate băncile."""

    def setUp(self):
        import server
        self.s, self.apeluri = server, []
        self.vechi = (server.celule_matrice, server.celule_rate, server.interoghează)
        server.celule_matrice = lambda *a: self.apeluri.append(("m",) + a) or [{"banca": "bcr"}]
        server.celule_rate = lambda *a: self.apeluri.append(("r",) + a) or [{"banca": "ing"}]
        self.monede = []
        self.vechi_monede = server._alte_monede_rate
        server._alte_monede_rate = lambda *a: self.monede.append(a) or {"ing": {"n": 1, "din": 4}}

    def tearDown(self):
        self.s.celule_matrice, self.s.celule_rate, self.s.interoghează = self.vechi
        self.s._alte_monede_rate = self.vechi_monede

    def test_comision_pe_pf_implicit(self):
        c = self.s._clasament_vox("administrare_cont", None, None, None, None)
        self.assertEqual((c["sursa"], c["grup"], c["unitate"], c["sens"], c["segment"]),
                         ("matrice", "cont_curent", "lei", "mic_bun", "pf"))
        self.assertEqual(c["blocuri"], [{"tip": "exact", "termen": "", "produs": "", "celule": [{"banca": "bcr"}]}])
        self.assertEqual(self.apeluri, [("m", ["administrare_cont"], "lei", "pf")])

    def test_comision_segment_cerut_sau_necunoscut(self):
        self.s._clasament_vox("emitere_card", None, None, None, "pj")
        self.s._clasament_vox("emitere_card", None, None, None, "PF")
        self.assertEqual([a[3] for a in self.apeluri], ["pj", "pf"])

    def test_dobanda_cu_termen_doua_blocuri(self):
        """Pe 7–12 luni doar 2 bănci au termenul scris în sursă, 9 au dobânzi fără termen (07.10.2026):
        al doilea bloc le arată separat, fără să amestece termenele."""
        c = self.s._clasament_vox("nominala", "depozite", "12", None, None)
        self.assertEqual((c["sursa"], c["grup"], c["unitate"], c["sens"]), ("rate", "depozite", "procent", "mare_bun"))
        self.assertEqual([(b["tip"], b["termen"], b["produs"]) for b in c["blocuri"]],
                         [("exact", "12", ""), ("nespecificat", "necunoscut", "")])
        self.assertEqual(self.apeluri, [("r", ["nominala"], "depozite", "12", ""),
                                        ("r", ["nominala"], "depozite", "necunoscut", "")])

    def test_credit_cu_produs(self):
        c = self.s._clasament_vox("dae", "credite", None, "ipotecar", None)
        self.assertEqual([(b["tip"], b["termen"], b["produs"]) for b in c["blocuri"]],
                         [("exact", "", "ipotecar"), ("nespecificat", "", "altele")])

    def test_dobanda_fara_filtre_un_bloc(self):
        c = self.s._clasament_vox("dae", "credite", None, None, None)
        self.assertEqual(len(c["blocuri"]), 1)

    def test_dobanda_spune_alte_monede(self):
        """La depozitul pe 12 luni, ambele valori Raiffeisen sunt în altă monedă (mip_merge, 08.10.2026):
        clasamentul păstrează cifra din 2.2, dar o marchează, în fiecare bloc."""
        c = self.s._clasament_vox("nominala", "depozite", "12", None, None)
        self.assertEqual([b["celule"] for b in c["blocuri"]],
                         [[{"banca": "ing", "alte_monede": {"n": 1, "din": 4}}]] * 2)
        self.assertEqual(self.monede, [(["nominala"], "depozite", "12", ""),
                                       (["nominala"], "depozite", "necunoscut", "")])

    def test_comision_fara_alte_monede(self):
        self.s._clasament_vox("administrare_cont", None, None, None, None)
        self.assertEqual(self.monede, [])

    def test_neclasabil(self):
        for args in (("schimbare_pin", None, None, None, None), ("nominala", None, None, None, None),
                     ("dae", "depozite", None, None, None), (None, None, None, None, None)):
            self.assertIsNone(self.s._clasament_vox(*args), args)
        self.assertEqual(self.apeluri, [])

    def test_stare_pe_toate_bancile(self):
        self.s.interoghează = lambda sql, params=None: [
            {"slug": "ing", "surse": 158, "blocate": 48, "robots": 48, "pdf": 48},
            {"slug": "cec", "surse": 1, "blocate": 1, "robots": 0, "pdf": 0}]
        s = self.s._stare_banci_vox()
        self.assertEqual(s["ing"], {"stare": None, "surse": 158, "robots": 48, "refuzate": 0, "pdf": 48})
        self.assertEqual(s["cec"]["stare"], "blocata")

    def test_context_clasabile_din_grupuri(self):
        self.s.interoghează = lambda sql, params=None: []
        cl = self.s._context_vox()["clasabile"]
        self.assertEqual(len(cl["comisioane"]), 14)
        self.assertIn("administrare_cont", cl["comisioane"])
        self.assertEqual(cl["dobanzi"]["dae"], ["credite"])
        self.assertEqual(cl["dobanzi"]["nominala"], ["conturi_carduri", "credite", "depozite"])


class CititoriAplicatii(unittest.TestCase):
    """Cititorii din server pentru aplicații: contextul promptului, analiza APK, App Store, Google Play."""

    def setUp(self):
        import server
        self.s = server
        self.vechi = (server.interoghează, server.FISIER_GOOGLE_PLAY)
        self.dir = tempfile.mkdtemp(prefix="vox_play_")

    def tearDown(self):
        self.s.interoghează, self.s.FISIER_GOOGLE_PLAY = self.vechi

    def baza(self, sql, params=None):
        if "SELECT functie, min(titlu)" in sql:
            return [{"functie": "ropay", "titlu": "RoPay (plăți instant din cont)"}]
        if "SELECT b.slug AS banca, a.aplicatie FROM" in sql:
            return [{"banca": "bcr", "aplicatie": "George Romania"}]
        if "FROM android_aplicatii" in sql:
            return [{"banca": "bcr", "package": "ro.bcr.georgego", "aplicatie": "George Romania", "rol": "principal",
                     "versiune_analizata": "1.0", "framework": "nativ", "data_analizei": "2026-10-01"}]
        if "FROM android_functionalitati" in sql:
            return [{"package": "ro.bcr.georgego", "functie": "ropay", "verdict": "sigur", "surse": "cod|text",
                     "dovada_text": "RoPay"}]
        if "FROM app_release_curente" in sql:
            return [{"banca": "bcr", "app_id": "123", "nota": 4.84, "evaluari": 188573,
                     "distributie_stele": [1, 0, 0, 0, 0], "versiune": "26.30", "observat_la": "2026-09-24"}]
        return []

    def play(self, continut):
        cale = os.path.join(self.dir, "google_play.json")
        with open(cale, "w", encoding="utf-8") as f:
            f.write(continut)
        self.s.FISIER_GOOGLE_PLAY = cale

    def test_context_functii_si_aplicatii(self):
        self.s.interoghează = self.baza
        ctx = self.s._context_vox()
        self.assertEqual(ctx["functii"], [{"functie": "ropay", "titlu": "RoPay (plăți instant din cont)"}])
        self.assertEqual(ctx["aplicatii"], [{"banca": "bcr", "aplicatie": "George Romania"}])

    def test_aplicatii_din_baza_si_fisier(self):
        self.s.interoghează = self.baza
        self.play(json.dumps({"colectat_la": "2026-10-06T09:39:43Z",
                              "aplicatii": {"bcr": {"nota": 4.81, "evaluari": 155826}}}))
        d = self.s._aplicatii_vox()
        self.assertEqual(d["aplicatii"][0]["package"], "ro.bcr.georgego")
        self.assertEqual(d["functii"][0]["verdict"], "sigur")
        self.assertEqual(d["app_store"][0]["nota"], 4.84)
        self.assertEqual(d["play"], {"colectat_la": "2026-10-06", "aplicatii": {"bcr": {"nota": 4.81, "evaluari": 155826}}})

    def test_google_play_lipsa_sau_stricat(self):
        """`date/google_play.json` e în afara git: lipsește pe alt laptop și pe mcc-test; Vox merge fără el."""
        self.s.FISIER_GOOGLE_PLAY = os.path.join(self.dir, "nu_exista.json")
        self.assertIsNone(self.s._google_play())
        for stricat in ("{", "[]", json.dumps({"colectat_la": "2026-10-06"}), json.dumps({"aplicatii": []})):
            self.play(stricat)
            self.assertIsNone(self.s._google_play(), stricat)


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
        # un Host străin e refuzat deja la poartă (401: nu e utilizator local); unul local cu alt port, la Vox (403)
        self.assertIn(self.cere("GET", "/api/vox", host=f"evil.com:{self.port}")[0], (401, 403))
        self.assertEqual(self.cere("GET", "/api/vox", host="localhost:1")[0], 403)

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
            # Host străin: refuz la poartă (401); restul, inclusiv localhost:5173: refuz la verificarea lui Vox (403)
            self.assertIn(cod, (401, 403) if host == f"evil.com:{self.port}" else (403,), (antete, host))
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

    def test_post_buton_fara_model(self):
        """„Compară cu Libra” sub un răspuns: același drum ca întrebarea, fără apel la model (08.10.2026)."""
        ok = {"X-MIP-Token": self.token()}
        n = len(self.client.cereri)
        cod, d = self.cere("POST", "/api/vox", {"buton": "libra", "anterior": interp()}, ok)
        self.assertEqual(cod, 200, d)
        self.assertEqual((d["model"], d["cost_usd"], d["buton"]), (None, 0, "libra"))
        self.assertEqual([r["banca"] for r in d["raspunsuri"]], ["bcr", "libra"])
        self.assertEqual(len(self.client.cereri), n)

    def test_post_buton_refuzat(self):
        ok = {"X-MIP-Token": self.token()}
        n = len(self.client.cereri)
        for corp in ({"buton": "toate", "anterior": interp()},
                     {"buton": "firme", "anterior": interp(concept="nominala", categorie="depozite")},
                     {"buton": "libra", "anterior": interp(), "intrebare": "BCR?"},
                     {"buton": "libra"}):
            self.assertEqual(self.cere("POST", "/api/vox", corp, ok)[0], 400, corp)
        self.assertEqual(self.cere("POST", "/api/vox", {"buton": "libra", "anterior": interp()})[0], 403)
        self.assertEqual(len(self.client.cereri), n)               # niciun apel plătit

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
                # Host străin: refuz la poartă (401); restul: refuz la verificarea lui Vox (403)
                self.assertIn(cod, (401, 403) if host else (403,), (antete, host, actiune))
        cod, _ = self.cere("POST", f"/api/vox/conversatii/{c}/sterge", None, dict(ok, **{"Content-Type": "text/plain"}))
        self.assertEqual(cod, 415)
        self.assertIn(self.cere("GET", "/api/vox/conversatii", host=f"evil.com:{self.port}")[0], (401, 403))
        self.assertEqual(self.cere("GET", "/api/vox/conversatii", host="localhost:1")[0], 403)
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

    def test_scrierea_de_o_ora(self):
        self.assertAlmostEqual(vox.preturi.cost("claude-haiku-4-5", scriere_cache_1h=1_000_000), 2.0)
        self.assertAlmostEqual(vox.preturi.cost("claude-haiku-4-5", scriere_cache=1_000_000), 1.25)


if __name__ == "__main__":
    unittest.main(verbosity=2)
