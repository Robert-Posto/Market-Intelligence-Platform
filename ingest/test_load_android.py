"""Teste pentru load_android.py: valorile text rămân exacte și pachetul modificat e refuzat.

Rulare:  python ingest/test_load_android.py
"""
import csv
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
import load_android as L  # noqa: E402


class TestValoare(unittest.TestCase):
    def test_spatiul_si_nbsp_raman_valori(self):
        self.assertEqual(L.valoare("valoare", " ", set()), " ")
        self.assertEqual(L.valoare("text", "\xa0", set()), "\xa0")

    def test_celula_goala_devine_null(self):
        self.assertIsNone(L.valoare("valoare", "", set()))
        self.assertIsNone(L.valoare("pas", " ", {"pas"}))

    def test_intregi(self):
        self.assertEqual(L.valoare("pas", " 3 ", {"pas"}), 3)


class TestManifest(unittest.TestCase):
    def pachet(self):
        d = tempfile.mkdtemp(prefix="android_test_")
        os.makedirs(os.path.join(d, "date"))
        rows = []
        for f in ["aplicatii.csv", *L.TABELE]:
            p = os.path.join(d, "date", f)
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write("package\nx\n")
            rows.append((f"date/{f}", hashlib.sha256(open(p, "rb").read()).hexdigest()))
        with open(os.path.join(d, "MANIFEST.csv"), "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["fisier", "octeti", "sha256"])
            for f, h in rows:
                w.writerow([f, 0, h])
        return d

    def test_pachet_intact_trece(self):
        d = self.pachet()
        try:
            L.verifica_manifest(d)
        finally:
            shutil.rmtree(d)

    def test_fisier_modificat_e_refuzat(self):
        d = self.pachet()
        try:
            with open(os.path.join(d, "date", "permisiuni.csv"), "a", encoding="utf-8") as fh:
                fh.write("adaugat\n")
            with self.assertRaises(SystemExit):
                L.verifica_manifest(d)
        finally:
            shutil.rmtree(d)

    def test_uscat_nu_cere_baza(self):
        d = self.pachet()
        try:
            r = subprocess.run([sys.executable, os.path.join(AICI, "load_android.py"), d, "--uscat"],
                               capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("sha256 verificat", r.stdout)
        finally:
            shutil.rmtree(d)

    def test_provenienta_din_numele_pachetului(self):
        self.assertEqual(L.provenienta_implicita(r"C:\x\MIP_android_pentru_Robert_2026-10-05"),
                         "android_static_2026-10-05")


if __name__ == "__main__":
    unittest.main()
