"""Ruta /pdf ca proxy: garda de rețea internă pe fiecare pas, redirecturi urmate de noi,
plafonul de mărime și lista albă ținută doar pe pozitive (auditul de securitate, B3).

Fără rețea: sesiunea HTTP e falsă, rezolvitorul DNS e injectat, iar fișierele lui flux
(copii robots.txt, jurnalul BLOCAT, cozile) și cache-ul PDF stau într-un folder temporar.

Rulare:  python app/test_pdf_proxy.py
"""

import io
import os
import socket
import sys
import tempfile
import unittest
from unittest import mock

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AICI)
sys.path.insert(0, os.path.join(os.path.dirname(AICI), "ingest"))

import requests  # noqa: E402
from requests.structures import CaseInsensitiveDict  # noqa: E402

import server  # noqa: E402
import destinatie  # noqa: E402
import flux  # noqa: E402
import transport  # noqa: E402
from crawler.robots import RegulliRobots  # noqa: E402

PDF = b"%PDF-1.7\n" + b"x" * 2000
PUBLIC = "93.184.216.34"


def rezolvitor(adrese):
    """getaddrinfo fals: gazdă -> IP-uri; o gazdă nenumită e publică."""
    def rezolva(gazda, port, *a, **kw):
        return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))
                for ip in adrese.get(gazda, [PUBLIC])]
    return rezolva


def raspuns(status=200, corp=b"", antete=None):
    r = requests.Response()
    r.status_code = status
    r.headers = CaseInsensitiveDict(antete if antete is not None else {"Content-Type": "application/pdf"})
    r.raw = io.BytesIO(corp)
    return r


class Sesiune:
    """Ține minte fiecare cerere; răspunsurile vin dintr-un dicționar adresă -> fabrică."""

    def __init__(self, raspunsuri):
        self.raspunsuri, self.cereri = raspunsuri, []

    def get(self, url, **kw):
        self.cereri.append((url, kw))
        return self.raspunsuri[url]()


class Proxy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.patchuri = [
            mock.patch.object(server, "CACHE_PDF", os.path.join(d, "cache_pdf")),
            mock.patch.object(flux, "DIR_ROBOTS", os.path.join(d, "robots")),
            mock.patch.object(flux, "JURNAL_BLOCAT", os.path.join(d, "origini_blocate.jsonl")),
            mock.patch.object(flux, "DIR_COADA", os.path.join(d, "origini")),
            mock.patch.object(flux, "_CACHE_ROBOTS", {}),
            mock.patch.object(flux, "_BLOCATE", None),
            mock.patch.object(flux, "_RESETARI", flux.collections.Counter()),
            mock.patch.object(destinatie, "rezolva", rezolvitor({"intern.banca.example": ["10.0.0.5"],
                                                                 "rebind.banca.example": [PUBLIC, "127.0.0.1"]})),
            # nicio cerere reală: nici robots.txt, nici PDF-ul (testele dau sesiunea lor)
            mock.patch("requests.get", side_effect=AssertionError("cerere reală")),
        ]
        for p in self.patchuri:
            p.start()
        for origine in ("https://banca.example", "https://cdn.banca.example"):
            flux._CACHE_ROBOTS[origine] = self.reguli(origine)

    def tearDown(self):
        for p in reversed(self.patchuri):
            p.stop()
        self.tmp.cleanup()

    @staticmethod
    def reguli(origine, text=""):
        rr = RegulliRobots("test", origine)
        rr._parseaza(text)
        rr.status = "test"
        return rr

    def test_adrese_interne_refuzate_fara_nicio_cerere(self):
        s = Sesiune({})
        for url in ("https://127.0.0.1/a.pdf", "https://10.1.2.3/a.pdf", "https://172.16.0.1/a.pdf",
                    "https://192.168.1.1/a.pdf", "https://169.254.169.254/latest/meta-data/",
                    "https://[::1]/a.pdf", "https://[::ffff:127.0.0.1]/a.pdf", "https://100.64.0.1/a.pdf",
                    "https://0.0.0.0/a.pdf", "https://intern.banca.example/a.pdf",
                    "https://rebind.banca.example/a.pdf", "file:///C:/Windows/win.ini"):
            with self.assertRaises(PermissionError, msg=url):
                server._adu_din_retea(url, s)
        self.assertEqual(s.cereri, [])

    def test_adresa_publica_se_aduce(self):
        s = Sesiune({"https://banca.example/a.pdf": lambda: raspuns(200, PDF)})
        cale = server._adu_din_retea("https://banca.example/a.pdf", s)
        with open(cale, "rb") as f:
            self.assertEqual(f.read(), PDF)
        ((url, kw),) = s.cereri
        self.assertEqual((kw["allow_redirects"], kw["stream"], kw["timeout"]), (False, True, 40))
        # a doua oară din cache, fără cerere
        self.assertEqual(server._adu_din_retea("https://banca.example/a.pdf", s), cale)
        self.assertEqual(len(s.cereri), 1)

    def test_redirect_urmat_cu_garda_pe_fiecare_pas(self):
        s = Sesiune({
            "https://banca.example/a.pdf": lambda: raspuns(302, antete={"Location": "https://cdn.banca.example/a.pdf"}),
            "https://cdn.banca.example/a.pdf": lambda: raspuns(200, PDF)})
        server._adu_din_retea("https://banca.example/a.pdf", s)
        self.assertEqual([u for u, _ in s.cereri], ["https://banca.example/a.pdf", "https://cdn.banca.example/a.pdf"])

    def test_al_doilea_pas_spre_retea_interna(self):
        for tinta in ("http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:8765/api/sumar",
                      "https://intern.banca.example/x.pdf", "http://[::1]/x"):
            s = Sesiune({
                "https://banca.example/a.pdf": lambda: raspuns(301, antete={"Location": "https://cdn.banca.example/b"}),
                "https://cdn.banca.example/b": lambda t=tinta: raspuns(302, antete={"Location": t})})
            with self.assertRaises(PermissionError, msg=tinta):
                server._adu_din_retea("https://banca.example/a.pdf", s)
            self.assertEqual([u for u, _ in s.cereri],
                             ["https://banca.example/a.pdf", "https://cdn.banca.example/b"], tinta)

    def test_robots_pe_pasul_redirectului(self):
        flux._CACHE_ROBOTS["https://cdn.banca.example"] = self.reguli(
            "https://cdn.banca.example", "User-agent: *\nDisallow: *.pdf\n")
        s = Sesiune({"https://banca.example/a.pdf": lambda: raspuns(
            302, antete={"Location": "https://cdn.banca.example/a.pdf"})})
        with self.assertRaises(PermissionError):
            server._adu_din_retea("https://banca.example/a.pdf", s)
        self.assertEqual(len(s.cereri), 1)

    def test_prea_multe_redirecturi(self):
        s = Sesiune({"https://banca.example/a.pdf": lambda: raspuns(
            302, antete={"Location": "https://banca.example/a.pdf"})})
        with self.assertRaises(ValueError):
            server._adu_din_retea("https://banca.example/a.pdf", s)
        self.assertEqual(len(s.cereri), transport.MAX_PASI_REDIRECT + 1)

    def test_corp_peste_plafon(self):
        with mock.patch.object(server, "MAX_PDF_OCTETI", 4096):
            mare = b"%PDF-1.7\n" + b"x" * 10000
            s = Sesiune({"https://banca.example/fara-lungime.pdf": lambda: raspuns(200, mare),
                         "https://banca.example/cu-lungime.pdf": lambda: raspuns(
                             200, mare, {"Content-Type": "application/pdf", "Content-Length": str(len(mare))})})
            for url in ("https://banca.example/fara-lungime.pdf", "https://banca.example/cu-lungime.pdf"):
                with self.assertRaises(ValueError, msg=url):
                    server._adu_din_retea(url, s)
            self.assertEqual(os.listdir(server.CACHE_PDF), [])

    def test_raspuns_care_nu_e_pdf_sau_eroare(self):
        s = Sesiune({"https://banca.example/html": lambda: raspuns(200, b"<html>" + b"x" * 2000),
                     "https://banca.example/500": lambda: raspuns(500, b"stack trace intern")})
        for url in ("https://banca.example/html", "https://banca.example/500"):
            with self.assertRaises(ValueError, msg=url):
                server._adu_din_retea(url, s)


class ListaAlba(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(server, "_PERMISE", set())
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_doar_pozitivele_raman_in_memorie(self):
        apeluri = []

        def interogheaza(sql, params=None):
            apeluri.append(params)
            return [{"?column?": 1}] if params[0] == "https://banca.example/a.pdf" else []
        with mock.patch.object(server, "interoghează", interogheaza):
            for _ in range(3):
                self.assertFalse(server.pdf_permis("https://oriunde.example/x.pdf"))
                self.assertTrue(server.pdf_permis("https://banca.example/a.pdf"))
            for i in range(50):
                server.pdf_permis(f"https://oriunde.example/{i}.pdf")
        self.assertEqual(server._PERMISE, {"https://banca.example/a.pdf"})
        # pozitivul se cere o dată; refuzul de fiecare dată (nu ocupă memorie și
        # devine permis imediat ce pipeline-ul înregistrează documentul)
        self.assertEqual(sum(1 for p in apeluri if p[0] == "https://banca.example/a.pdf"), 1)
        self.assertEqual(sum(1 for p in apeluri if p[0] == "https://oriunde.example/x.pdf"), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
