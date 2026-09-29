"""Teste pentru încărcarea catalogului Libra: parsarea rândurilor și cheia
de idempotență. Fără bază de date."""

import os
import sys
import tempfile
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import load_catalog_libra as L
import normalizeaza as N

ANTET = ["Cod", "Denumire", "Categorie produs", "Produs prioritar", "Tip produs",
         "Adresabilitate", "Caracteristicile produsului", "Criterii de eligibilitate",
         "Când să recomand acest produs", "Beneficiu pentru client",
         "Sursa / document intern", "Cifră de afaceri minimă (lei)",
         "Cifră de afaceri maximă (lei)", "Angajați minim",
         "Vechime minimă firmă (ani)", "Vechime maximă firmă (ani)",
         "Linii de business eligibile", "CAEN eligibile (prefixe)"]


def rand(**kw):
    v = dict.fromkeys(ANTET)
    v.update(kw)
    return [v[h] for h in ANTET]


class TestParsare(unittest.TestCase):
    def test_rand_complet(self):
        r = L.parseaza_rand(ANTET, rand(
            **{"Cod": "ABONAMENT_RISE", "Denumire": "Abonament RISE",
               "Categorie produs": "Cont curent & operațiuni (CONT_CURENT)",
               "Produs prioritar": "Da", "Adresabilitate": "Doar persoane juridice",
               "Cifră de afaceri maximă (lei)": 5000000, "Tip produs": "CARD CREDIT ",
               "Beneficiu pentru client": ""}), 7, "f.xlsx", "Catalog produse")
        self.assertEqual((r["cod"], r["categorie_cod"], r["segment"]),
                         ("ABONAMENT_RISE", "CONT_CURENT", "PJ"))
        self.assertTrue(r["produs_prioritar"])
        self.assertEqual(r["cifra_afaceri_max"], 5000000)
        self.assertIsNone(r["cifra_afaceri_min"])
        self.assertIsNone(r["beneficiu_client"])          # gol -> NULL
        self.assertEqual(r["tip_produs"], "CARD CREDIT")   # tăiat la capete
        self.assertEqual(r["rand_brut"]["Tip produs"], "CARD CREDIT ")  # brutul e neatins
        self.assertEqual(r["rand_brut"]["Beneficiu pentru client"], "")
        self.assertEqual(len(r["rand_brut"]), len(ANTET))

    def test_segmente_si_categorie_lipsa(self):
        for text, seg in (("Doar persoane fizice", "PF"), ("Oricine (PF și PJ)", "PF+PJ"),
                          ("altceva", None), (None, None)):
            r = L.parseaza_rand(ANTET, rand(Cod="X", Denumire="X", Adresabilitate=text),
                                2, "f", "g")
            self.assertEqual(r["segment"], seg)
            self.assertIsNone(r["categorie_cod"])
            self.assertFalse(r["produs_prioritar"])


class TestCitire(unittest.TestCase):
    def test_fisier_si_cheie(self):
        import openpyxl
        wb = openpyxl.Workbook()
        s = wb.active
        s.title = "Sumar"
        s.append(["Generat la", "28.09.2026, 14:29:51"])
        c = wb.create_sheet("Catalog produse")
        c.append(ANTET)
        c.append(rand(Cod="A", Denumire="Produs A"))
        c.append([None] * len(ANTET))                     # rând gol: se sare
        c.append(rand(Cod="B", Denumire="Produs B"))
        with tempfile.TemporaryDirectory() as d:
            cale = os.path.join(d, "cat.xlsx")
            wb.save(cale)
            r1, r2 = L.citeste(cale), L.citeste(cale)
        self.assertEqual([x["cod"] for x in r1], ["A", "B"])
        self.assertEqual([x["rand"] for x in r1], [2, 4])  # numărul rândului din foaie
        # aceeași cheie la reîncărcare -> upsert, nu dublare
        cheie = lambda rr: [(x["fisier"], x["foaie"], x["rand"]) for x in rr]
        self.assertEqual(cheie(r1), cheie(r2))
        self.assertEqual(len(set(cheie(r1))), 2)
        self.assertEqual(r1[0]["generat_la"].year, 2026)


class TestRegulaCatalog(unittest.TestCase):
    def test_libra_in_catalog(self):
        self.assertIn("libra", N.BANCI_CU_CATALOG)
        self.assertNotIn("bcr", N.BANCI_CU_CATALOG)


if __name__ == "__main__":
    unittest.main()
