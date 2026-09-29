"""Teste pentru migrarea 023: valorile din pagini de campanie și din
regulamente de campanie sunt ascunse în `observatii_curente`, nu șterse.

Rulează pe baza locală (containerul mip-db), după
db/migration_023_valori_din_campanii.sql sau db/sincronizeaza_vederi.sql:
    python ingest/test_valori_din_campanii.py
"""

import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import psycopg2

import normalizeaza as N

RADACINA = os.path.dirname(AICI)

# Câte valori curente ascunde regula pe baza din 29.09.2026 (înainte: 24.601
# valori curente, după: 24.274). Dacă baza se repopulează, cifra se schimbă:
# o verifici cu interogarea din `test_numarul_valorilor_ascunse` și o
# actualizezi aici, după ce te uiți ce s-a schimbat.
ASCUNSE_LA_29_09 = 327
EXCEPTII_LA_29_09 = 6

# o observație e „curentă" după regulile de dinainte de 023
CURENTA = "(o.stare_data IS NULL OR o.stare_data NOT IN ('ISTORIC', 'DUBLURA', 'VIITOR'))"


class TestValoriDinCampanii(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(N.dsn())
        cls.conn.set_session(readonly=True)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def unu(self, sql, *param):
        with self.conn.cursor() as cur:
            cur.execute(sql, param)
            return cur.fetchone()[0]

    def test_cetelem_fara_dobanda_nominala_zero_la_credite(self):
        # înainte: 6 valori de 0%, toate din cetelem.ro/promotii-credite-*
        n = self.unu("""
            SELECT count(*) FROM observatii_curente o
            JOIN surse s ON s.id = o.id_sursa JOIN banci b ON b.id = s.id_banca
            WHERE b.slug = 'cetelem' AND o.camp = 'nominala' AND o.valoare_num = 0
              AND o.cod_scenariu LIKE 'credite%%'""")
        self.assertEqual(n, 0)
        n = self.unu("""
            SELECT count(*) FROM observatii_curente o JOIN surse s ON s.id = o.id_sursa
            WHERE s.sursa LIKE '%%cetelem.ro/promotii-credite-%%'""")
        self.assertEqual(n, 0)

    def test_valorile_ascunse_raman_in_observations(self):
        n = self.unu("""
            SELECT count(*) FROM observations o JOIN surse s ON s.id = o.id_sursa
            WHERE s.sursa LIKE '%%cetelem.ro/promotii-credite-%%'
              AND o.camp = 'nominala' AND o.valoare_num = 0""")
        self.assertGreater(n, 0)
        # fiecare rând din vedere e o observație existentă
        lipsa = self.unu("""
            SELECT count(*) FROM observatii_din_campanii c
            WHERE NOT EXISTS (SELECT 1 FROM observations o WHERE o.id = c.id)""")
        self.assertEqual(lipsa, 0)
        # iar cele fără excepție chiar lipsesc din observatii_curente
        vizibile = self.unu("""
            SELECT count(*) FROM observatii_din_campanii c
            JOIN observatii_curente o ON o.id = c.id WHERE c.exceptie IS NULL""")
        self.assertEqual(vizibile, 0)

    def test_numarul_valorilor_ascunse(self):
        ascunse = self.unu(f"""
            SELECT count(*) FROM observatii_din_campanii c JOIN observations o ON o.id = c.id
            WHERE c.exceptie IS NULL AND {CURENTA}
              AND NOT EXISTS (SELECT 1 FROM observatii_inlocuite_de_catalog i
                              WHERE i.id = o.id)""")
        self.assertEqual(ascunse, ASCUNSE_LA_29_09)
        # și exact atâtea lipsesc din observatii_curente față de regula de dinainte
        inainte = self.unu(f"""
            SELECT count(*) FROM observations o WHERE {CURENTA}
              AND NOT EXISTS (SELECT 1 FROM observatii_inlocuite_de_catalog i
                              WHERE i.id = o.id)""")
        dupa = self.unu("SELECT count(*) FROM observatii_curente")
        self.assertEqual(inainte - dupa, ascunse)

    def test_exceptiile_raman_vizibile(self):
        with self.conn.cursor() as cur:
            cur.execute(f"""
                SELECT count(*), count(oc.id) FROM observatii_din_campanii c
                JOIN observations o ON o.id = c.id
                LEFT JOIN observatii_curente oc ON oc.id = c.id
                WHERE c.exceptie IS NOT NULL AND {CURENTA}""")
            n, vizibile = cur.fetchone()
        self.assertEqual(n, EXCEPTII_LA_29_09)
        self.assertEqual(vizibile, n)
        # dobânda standard a cardului de credit BRD (26%) rămâne, doar ea și DAE
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT o.camp, o.valoare_num FROM observatii_curente o
                JOIN observatii_din_campanii c ON c.id = o.id ORDER BY 1, 2""")
            self.assertEqual([(c, float(v)) for c, v in cur.fetchall()],
                             [("dae", 30.43), ("dae", 30.82), ("nominala", 26.0)])

    def test_regula_pe_url(self):
        def in_vedere(fragment):
            return self.unu("""
                SELECT count(*) FROM observatii_din_campanii WHERE sursa LIKE %s""",
                f"%{fragment}%")
        # prinse
        for f in ("cetelem.ro/promotii-credite-", "garantibbva.ro/campanii-incheiate/",
                  "garantibbva.ro/en/ended-campains/", "Regulament-campanie-Depozitul-Promo",
                  "castiga-ti-bicicleta", "bonus-500-lei-la-creditul-imobiliar"):
            self.assertGreater(in_vedere(f), 0, f)
        # lăsate vizibile: pagini de produs și programe permanente
        for f in ("garantibbva.ro/persoane-fizice/bonus-card/",          # „bonus-card" e numele
                  "castigam-cota-de-piata",                             # interviu, nu concurs
                  "oferta-credite-imobiliare-procredit-bank",           # oferta standard
                  "brd.ro/card-de-credit-oferte",                       # pagina cardului
                  "Regulamentul-oficial-al-programului-de-plata-in-rate",
                  "regulament-aa1-aa2-aa3-program-loialitate-card-emag",
                  "bcr.ro/ro/persoane-fizice/economisire-si-investire/depozitul-la-termen"):
            self.assertEqual(in_vedere(f), 0, f)

    def test_bcr_6_la_depozit_ramane_de_pe_pagina_produsului(self):
        n = self.unu("""
            SELECT count(*) FROM observatii_curente o JOIN surse s ON s.id = o.id_sursa
            WHERE s.sursa LIKE '%%bcr.ro/ro/persoane-fizice/economisire-si-investire/depozitul-la-termen'
              AND o.camp = 'nominala' AND o.valoare_num = 6""")
        self.assertGreater(n, 0)


class TestSincronizare(unittest.TestCase):
    def test_blocul_identic_in_migrare_si_in_sincronizare(self):
        def bloc(nume):
            with open(os.path.join(RADACINA, "db", nume), encoding="utf-8") as f:
                sql = f.read()
            i = sql.index("-- >>> observatii_din_campanii")
            j = sql.index("-- <<< observatii_din_campanii")
            return sql[i:j]
        self.assertEqual(bloc("migration_023_valori_din_campanii.sql"),
                         bloc("sincronizeaza_vederi.sql"))

    def test_observatii_curente_identica(self):
        def vedere(nume):
            with open(os.path.join(RADACINA, "db", nume), encoding="utf-8") as f:
                sql = f.read()
            i = sql.index("CREATE VIEW observatii_curente")
            return sql[i:sql.index(";", i)]
        self.assertEqual(vedere("migration_023_valori_din_campanii.sql"),
                         vedere("sincronizeaza_vederi.sql"))


if __name__ == "__main__":
    unittest.main()
