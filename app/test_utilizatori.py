"""Teste pentru app/utilizatori.py, pe un Postgres real (regulile țin de tranzacții și de FOR UPDATE).

Rulare, pe o bază de test (tabela se golește la fiecare test, deci NU pe baza aplicației):
    MIP_TEST_DSN="host=localhost port=55432 dbname=mip_test user=mip password=mip" python app/test_utilizatori.py
Fără MIP_TEST_DSN testele se sar.
"""

import os
import sys
import threading
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import psycopg2  # noqa: E402

import utilizatori  # noqa: E402

DSN = os.environ.get("MIP_TEST_DSN")
MIGRARE = os.path.join(os.path.dirname(AICI), "db", "migration_040_utilizatori.sql")


@unittest.skipUnless(DSN, "MIP_TEST_DSN nesetat: testele cer o bază Postgres de test")
class Utilizatori(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(MIGRARE, encoding="utf-8") as f:
            sql = f.read()
        with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute(sql)

    def setUp(self):
        with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute("TRUNCATE utilizatori")
        self.u = utilizatori.Utilizatori(DSN, admin_initial="Doru.Popescu")

    def rand(self, utilizator):
        return {r["utilizator"]: r for r in self.u.lista()["utilizatori"]}.get(utilizator)

    def admini(self, *nume):
        for n in nume:
            self.u.la_logare(n, n.title())
            with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
                cur.execute("UPDATE utilizatori SET rol = 'admin' WHERE utilizator = %s", (n,))

    # ---------------- prima logare

    def test_contul_nou_apare_fara_rol(self):
        self.assertIsNone(self.u.la_logare("ana", "Ana Analist"))
        r = self.rand("ana")
        self.assertEqual((r["nume"], r["rol"], r["activ"]), ("Ana Analist", None, True))
        self.assertIsNotNone(r["ultima_logare"])

    def test_adminul_initial_doar_la_creare(self):
        self.assertEqual(self.u.la_logare("doru.popescu", "Doru"), "admin")
        self.admini("adi")
        self.u.modifica("doru.popescu", {"rol": "analist"}, "adi")
        # la logarea următoare MCC_ADMIN_INITIAL nu-i redă rolul luat de alt admin
        self.assertEqual(self.u.la_logare("doru.popescu", "Doru"), "analist")

    def test_numele_din_ad_se_actualizeaza_rolul_nu(self):
        self.u.la_logare("ana", "Ana")
        self.u.modifica("ana", {"rol": "analist"}, "local")
        self.assertEqual(self.u.la_logare("ana", "Ana Popescu"), "analist")
        self.assertEqual(self.rand("ana")["nume"], "Ana Popescu")
        self.u.la_logare("ana", "  ")
        self.assertEqual(self.rand("ana")["nume"], "ana")      # displayName gol: numele contului

    def test_contul_dezactivat_nu_intra(self):
        self.u.la_logare("ana", "Ana")
        self.u.modifica("ana", {"rol": "analist", "activ": False}, "local")
        self.assertIsNone(self.u.la_logare("ana", "Ana"))
        self.assertEqual(self.rand("ana")["rol"], "analist")   # rolul rămâne, pentru reactivare

    # ---------------- modificarea

    def test_modifica_scrie_cine_si_cand(self):
        self.admini("adi")
        self.u.la_logare("ana", "Ana")
        nou, vechi = self.u.modifica("ana", {"rol": "analist"}, "adi")
        self.assertEqual((vechi["rol"], nou["rol"], nou["modificat_de"]), (None, "analist", "adi"))
        self.assertIsNotNone(nou["modificat"])

    def test_validari(self):
        self.u.la_logare("ana", "Ana")
        for corp, cod in (({"rol": "sef"}, "rol_invalid"), ({"activ": "da"}, "activ_invalid"),
                          ({"activ": 1}, "activ_invalid"), ({}, "nimic_de_modificat"),
                          ({"nume": "X"}, "nimic_de_modificat")):
            with self.assertRaises(utilizatori.Respins) as e:
                self.u.modifica("ana", corp, "local")
            self.assertEqual(e.exception.cod, cod, corp)
        for gresit in (None, "", 5, "x" * 65):
            with self.assertRaises(utilizatori.Respins):
                self.u.modifica(gresit, {"rol": "analist"}, "local")
        with self.assertRaises(utilizatori.Lipsa):
            self.u.modifica("nimeni", {"rol": "analist"}, "local")

    def test_nu_iti_retragi_singur_drepturile(self):
        self.admini("adi", "doru")
        for corp in ({"rol": "analist"}, {"rol": None}, {"activ": False}):
            with self.assertRaises(utilizatori.Respins) as e:
                self.u.modifica("adi", corp, "adi")
            self.assertEqual(e.exception.cod, "propriul_cont", corp)
        self.assertEqual(self.rand("adi")["rol"], "admin")
        self.u.modifica("adi", {"rol": "analist"}, "doru")     # altcineva poate

    def test_ultimul_admin_nu_se_retrage(self):
        self.admini("adi")
        self.u.la_logare("ana", "Ana")
        with self.assertRaises(utilizatori.Respins) as e:
            self.u.modifica("adi", {"activ": False}, "local")
        self.assertEqual(e.exception.cod, "ultimul_admin")
        # un admin dezactivat nu se numără: tot ultimul activ rămâne
        self.admini("doru")
        self.u.modifica("doru", {"activ": False}, "adi")
        with self.assertRaises(utilizatori.Respins):
            self.u.modifica("adi", {"rol": None}, "local")

    def test_doua_retrageri_simultane_lasa_un_admin(self):
        """Fiecare îl retrage pe celălalt în același moment: FOR UPDATE le pune la rând."""
        self.admini("adi", "doru")
        bariera, rezultate = threading.Barrier(2), {}

        def retrage(tinta, de_catre):
            bariera.wait()
            try:
                self.u.modifica(tinta, {"rol": "analist"}, de_catre)
                rezultate[tinta] = "ok"
            except utilizatori.Respins as exc:
                rezultate[tinta] = exc.cod
        fire = [threading.Thread(target=retrage, args=a) for a in (("adi", "doru"), ("doru", "adi"))]
        for f in fire:
            f.start()
        for f in fire:
            f.join()
        self.assertEqual(sorted(rezultate.values()), ["ok", "ultimul_admin"])
        self.assertEqual(sum(r["rol"] == "admin" for r in self.u.lista()["utilizatori"]), 1)

    def test_lista_neaprobatii_primii(self):
        self.admini("adi")
        self.u.la_logare("ana", "Ana")
        self.u.la_logare("ion", "Ion")
        self.u.modifica("ion", {"rol": "analist"}, "adi")
        self.assertEqual([r["utilizator"] for r in self.u.lista()["utilizatori"]][0], "ana")


if __name__ == "__main__":
    unittest.main(verbosity=2)
