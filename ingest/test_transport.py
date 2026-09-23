# ingest/test_transport.py
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import transport as T


class TestClasificare(unittest.TestCase):
    def test_coduri_de_blocaj(self):
        for cod in (401, 403, 407, 429, 451):
            self.assertEqual(T.clasifica_raspuns(cod, "text/html", b"x"), "BLOCAT")

    def test_blocaj_servit_cu_200(self):
        corp = b"<html><title>Access Denied</title>Reference #18.2f</html>"
        self.assertEqual(T.clasifica_raspuns(200, "text/html", corp), "BLOCAT")

    def test_503_cu_pagina_de_blocaj(self):
        self.assertEqual(T.clasifica_raspuns(503, "text/html", b"Just a moment..."), "BLOCAT")

    def test_503_simplu_se_reincearca(self):
        self.assertEqual(T.clasifica_raspuns(503, "text/html", b"maintenance"), "REINCEARCA")

    def test_disparut(self):
        self.assertEqual(T.clasifica_raspuns(404, "text/html", b""), "DISPARUT")

    def test_pdf(self):
        self.assertEqual(T.clasifica_raspuns(200, "application/pdf", b"%PDF-1.7 ..."), "OK")

    def test_pagina_js_goala(self):
        corp = b'<html><body><div id="root"></div>' + b"<script></script>" * 3 + b"</body></html>"
        self.assertEqual(T.clasifica_raspuns(200, "text/html", corp), "JS")

    def test_pagina_normala(self):
        corp = ("<html><body><main>" + "Depozit la termen 12 luni 5,5% " * 40
                + "</main></body></html>").encode()
        self.assertEqual(T.clasifica_raspuns(200, "text/html", corp), "OK")

    def test_redirect_serializat_in_corp(self):
        # Patria servea un 302 serializat în corpul unui răspuns 200
        corp = b"HTTP/1.0 302 Found\r\nLocation: https://www.patriabank.ro/x\r\n\r\n<!DOCTYPE html>"
        self.assertEqual(T.clasifica_raspuns(200, "text/html", corp), "REDIRECT_SERIALIZAT")


class TestEvidenta(unittest.TestCase):
    def test_evidenta_blocaj_200_cu_access_denied(self):
        # Test helper: a 200 body containing "Access Denied" yields evidence
        corp = b"<html><title>Access Denied</title>Reference #18.2f</html>"
        evidenta = T._evidenta_blocaj(200, corp)
        self.assertIsNotNone(evidenta)
        self.assertIn("Access Denied", evidenta)


if __name__ == "__main__":
    unittest.main()
