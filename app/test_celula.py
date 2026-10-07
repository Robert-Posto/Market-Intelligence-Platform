"""Teste fără bază pentru `/api/celula`: segmentul celulei și `strict`.

`interoghează` e înlocuit cu o funcție care ține minte interogarea, deci se verifică ce intră în SQL;
aceleași rânduri pe date reale le verifică scriptul pe `mip_merge` din planul
docs/superpowers/plans/2026-10-07-vox-raspunsuri.md.

Rulare:  python app/test_celula.py
"""

import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import server  # noqa: E402

# parametrii interogării de bază: banca, camp ×2, unitate ×2, categorie ×2
BAZA = ("bcr", "administrare_cont", "administrare_cont", "", "", "", "")


class Celula(unittest.TestCase):
    def setUp(self):
        self.cereri = []
        self.vechi = server.interoghează
        server.interoghează = lambda sql, params=None: self.cereri.append((sql, tuple(params or ()))) or []

    def tearDown(self):
        server.interoghează = self.vechi

    def cere(self, **q):
        server.celula({"banca": ["bcr"], "camp": ["administrare_cont"], **{k: [v] for k, v in q.items()}})
        sql, params = self.cereri[-1]
        self.assertEqual(sql.count("%s"), len(params))      # niciun parametru rătăcit
        return sql, params

    def fara_filtru_de_segment(self, sql):
        self.assertNotIn(server.COND_SEG, sql)
        self.assertNotIn(f"{server.SEGMENT_RAND} =", sql)
        self.assertNotIn(f"{server.SEGMENT_RAND} IS NULL", sql)

    def test_fara_segment_ca_inainte(self):
        sql, params = self.cere()
        self.fara_filtru_de_segment(sql)
        self.assertEqual(params, BAZA)

    def test_fiecare_rand_are_segmentul(self):
        sql, _ = self.cere()
        self.assertIn(f"{server.SEGMENT_RAND} AS segment", sql)

    def test_segmentul_cu_regula_din_2_1(self):
        """Sertarul din 2.1 filtrat pe PF arăta și valorile PJ: celula cere acum segmentul, cu aceeași
        regulă ca matricea (segmentul plus rândurile nemarcate)."""
        sql, params = self.cere(segment="pf")
        self.assertIn(f"AND ({server.COND_SEG})", sql)
        self.assertEqual(params, BAZA + ("pf",))

    def test_strict_doar_segmentul(self):
        sql, params = self.cere(segment="pj", strict="1")
        self.assertIn(f"AND {server.SEGMENT_RAND} = %s", sql)
        self.assertNotIn(server.COND_SEG, sql)
        self.assertEqual(params, BAZA + ("pj",))

    def test_nemarcat_doar_randurile_fara_segment(self):
        sql, params = self.cere(segment="nemarcat")
        self.assertIn(f"AND {server.SEGMENT_RAND} IS NULL", sql)
        self.assertEqual(params, BAZA)

    def test_segment_necunoscut_ignorat(self):
        """O adresă veche sau scrisă de mână („PF”, „toate”) nu dă 500 și nici un sertar gol."""
        for seg in ("toate", "PF", "x", "pf' OR 1=1 --"):
            sql, params = self.cere(segment=seg, strict="1")
            self.fara_filtru_de_segment(sql)
            self.assertEqual(params, BAZA)

    def test_strict_fara_segment_ignorat(self):
        sql, params = self.cere(strict="1")
        self.fara_filtru_de_segment(sql)
        self.assertEqual(params, BAZA)

    def test_parametrii_in_ordinea_conditiilor(self):
        """Produsul, cuvintele și segmentul își adaugă parametrii în ordinea în care intră în SQL."""
        sql, params = self.cere(camp="", text="datoria vamala", produs="ipotecar", segment="pf")
        self.assertEqual(params[7], "ipotecar")
        self.assertEqual(params[-1], "pf")
        self.assertTrue(params[8:-1] and all(p.startswith("%") for p in params[8:-1]))


class Matrice(unittest.TestCase):
    def test_matricea_foloseste_aceeasi_regula(self):
        cereri, vechi = [], server.interoghează
        server.interoghează = lambda sql, params=None: cereri.append((sql, tuple(params or ()))) or [{"n": 0}]
        try:
            server.matrice({"grup": ["cont_curent"], "segment": ["pf"], "unitate": ["lei"]})
        finally:
            server.interoghează = vechi
        self.assertIn(f"AND ({server.COND_SEG})", cereri[0][0])
        self.assertEqual(cereri[0][1][-1], "pf")


class CeluleSQL(unittest.TestCase):
    """Celulele din 2.1 și 2.2, scoase din `matrice` și `rate` ca să le folosească și clasamentele Vox."""

    def setUp(self):
        self.cereri, self.vechi = [], server.interoghează
        server.interoghează = lambda sql, params=None: self.cereri.append((sql, tuple(params or ()))) or []

    def tearDown(self):
        server.interoghează = self.vechi

    def test_matrice_segment_si_prag(self):
        server.celule_matrice(["administrare_cont"], "lei", "pf")
        sql, params = self.cereri[-1]
        self.assertIn(f"AND ({server.COND_SEG})", sql)
        self.assertIn(f"<= {server.PRAGURI['suma']}", sql)
        self.assertEqual(params, (["administrare_cont"], "lei", "pf"))

    def test_matrice_toate_fara_segment(self):
        server.celule_matrice(["administrare_cont"], "lei", "toate")
        sql, params = self.cereri[-1]
        self.assertNotIn(server.COND_SEG, sql)
        self.assertEqual(params, (["administrare_cont"], "lei"))

    def test_rate_termen_si_produs(self):
        server.celule_rate(["dae"], "credite", "lung", "ipotecar")
        sql, params = self.cereri[-1]
        self.assertIn(f"{server.TERMEN_LUNI} > 12", sql)
        self.assertIn(f"{server.PRODUS_CREDIT} = %s", sql)
        self.assertIn(f"<= {server.GRUPURI_RATE['credite']['prag']}", sql)
        self.assertEqual(params, (["dae"], "credite", "ipotecar"))

    def test_rate_fara_filtre(self):
        server.celule_rate(["nominala"], "depozite", "", "")
        sql, params = self.cereri[-1]
        self.assertNotIn(server.TERMEN_LUNI, sql.split("WITH randuri AS")[1].split("), agregat")[0].split("AS luni")[1])
        self.assertEqual(params, (["nominala"], "depozite"))

    def test_paginile_folosesc_celulele(self):
        apeluri = []
        server.celule_matrice, vechi_m = (lambda *a: apeluri.append(("m",) + a) or ["M"]), server.celule_matrice
        server.celule_rate, vechi_r = (lambda *a: apeluri.append(("r",) + a) or ["R"]), server.celule_rate
        # `rate` citește și meniul de filtre (luni, produs) din aceeași interogare falsă
        server.interoghează = lambda sql, params=None: [{"n": 0, "luni": None, "produs": "altele"}]
        try:
            m = server.matrice({"grup": ["carduri"], "segment": ["pj"], "unitate": ["eur"]})
            r = server.rate({"categorie": ["credite"], "termen": ["lung"], "produs": ["ipotecar"]})
        finally:
            server.celule_matrice, server.celule_rate = vechi_m, vechi_r
        self.assertEqual((m["celule"], r["celule"]), (["M"], ["R"]))
        self.assertEqual(apeluri, [("m", server.GRUPURI["carduri"]["campuri"], "eur", "pj"),
                                   ("r", server.GRUPURI_RATE["credite"]["campuri"], "credite", "lung", "ipotecar")])

    def test_mediana_aleasa_determinist(self):
        """La valori egale, rândul de la mediană era ales după planul interogării: clasamentul unui
        concept și matricea grupului lui arătau aceeași cifră cu alt serviciu, altă sursă sau altă pagină
        (29 din 46 de comparații, mip_merge, 07.10.2026). Cheia observației decide la egalitate."""
        server.celule_matrice(["administrare_cont"], "lei", "pf")
        server.celule_rate(["nominala"], "depozite", "", "")
        for sql, _ in self.cereri:
            self.assertIn("o.id AS id_obs", sql)
            self.assertIn("ORDER BY valoare_num, serviciu, id_obs) AS rn", sql)


if __name__ == "__main__":
    unittest.main(verbosity=2)
