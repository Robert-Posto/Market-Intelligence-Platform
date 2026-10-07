"""Extractorul zilnic, după auditul de securitate (B4): sursele propuse de model se
filtrează la scriere, iar orice descărcare trece, pe fiecare redirect, prin garda de
rețea internă, originea BLOCAT și robots.txt din ingest/transport.py, cu plafon de mărime.

Fără rețea și fără model: httpx primește un `MockTransport`, rezolvitorul DNS e injectat,
iar fișierele lui flux (copii robots.txt, jurnalul BLOCAT, cozile) stau într-un folder
temporar. Pe laptop lipsesc `trafilatura` și `selectolax`; descărcarea nu le folosește,
deci, dacă lipsesc, se pun în locul lor module goale doar pentru import.

Rulare:  python extragere_produse_bancare/test_garda_extragere.py
"""
from __future__ import annotations

import asyncio
import gzip
import importlib.util
import io
import os
import socket
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

AICI = Path(__file__).parent
RADACINA = AICI.parent
sys.path.insert(0, str(AICI))
sys.path.append(str(RADACINA))
sys.path.append(str(RADACINA / "ingest"))
for _nume in ("trafilatura", "selectolax", "selectolax.parser"):
    try:
        importlib.import_module(_nume)
    except ImportError:
        sys.modules[_nume] = types.ModuleType(_nume)
sys.modules["selectolax.parser"].__dict__.setdefault("HTMLParser", object)

import httpx  # noqa: E402

import destinatie  # noqa: E402
import flux  # noqa: E402
from crawler.robots import RegulliRobots  # noqa: E402


def _modul(nume: str, fisier: str):
    spec = importlib.util.spec_from_file_location(nume, AICI / fisier)
    m = importlib.util.module_from_spec(spec)
    sys.modules[nume] = m
    spec.loader.exec_module(m)
    return m


fh = _modul("flow_html", "flow-html.py")
import targetedCrawl as T  # noqa: E402

PUBLIC = "93.184.216.34"
PAGINA = b"<html><body>" + "Depozit la termen 12 luni 5,5% ".encode() * 40 + b"</body></html>"


def rezolvitor(adrese):
    def rezolva(gazda, port, *a, **kw):
        return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))
                for ip in adrese.get(gazda, [PUBLIC])]
    return rezolva


def reguli(origine, text=""):
    rr = RegulliRobots("test", origine)
    rr._parseaza(text)
    rr.status = "test"
    return rr


class Izolat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.patchuri = [
            mock.patch.object(flux, "DIR_ROBOTS", os.path.join(d, "robots")),
            mock.patch.object(flux, "JURNAL_BLOCAT", os.path.join(d, "origini_blocate.jsonl")),
            mock.patch.object(flux, "DIR_COADA", os.path.join(d, "origini")),
            mock.patch.object(flux, "_CACHE_ROBOTS", {}),
            mock.patch.object(flux, "_BLOCATE", None),
            mock.patch.object(destinatie, "rezolva", rezolvitor({"intern.bcr.ro": ["10.0.0.5"]})),
            # robots.txt e pus mai jos în cache; o cerere reală ar fi o greșeală a testului
            mock.patch("requests.get", side_effect=AssertionError("cerere reală")),
        ]
        for p in self.patchuri:
            p.start()
        for o in ("https://www.bcr.ro", "https://cdn.bcr.ro", "https://intern.bcr.ro"):
            flux._CACHE_ROBOTS[o] = reguli(o)
        flux._CACHE_ROBOTS["https://interzis.bcr.ro"] = reguli("https://interzis.bcr.ro",
                                                              "User-agent: *\nDisallow: /\n")
        self.cereri: list[str] = []

    def tearDown(self):
        for p in reversed(self.patchuri):
            p.stop()
        self.tmp.cleanup()

    def server(self, raspunsuri):
        """MockTransport: adresă -> (status, antete, corp); ține minte ce s-a cerut."""
        def handler(cerere):
            self.cereri.append(str(cerere.url))
            status, antete, corp = raspunsuri[str(cerere.url)]
            return httpx.Response(status, headers=antete, content=corp)
        return httpx.MockTransport(handler)

    def adu(self, url, raspunsuri, **kw):
        return asyncio.run(fh.adu_http(url, transport=self.server(raspunsuri), timeout=5, **kw))


class TestAduHttp(Izolat):
    def test_pagina_legitima_ca_inainte(self):
        r = self.adu("https://www.bcr.ro/depozite", {
            "https://www.bcr.ro/depozite": (200, {"Content-Type": "text/html; charset=utf-8"}, PAGINA)})
        self.assertEqual((r.status_code, r.content, str(r.url)), (200, PAGINA, "https://www.bcr.ro/depozite"))
        self.assertIn("Depozit", r.text)
        r.raise_for_status()

    def test_redirect_pe_domeniu_urmat(self):
        r = self.adu("https://www.bcr.ro/a", {
            "https://www.bcr.ro/a": (301, {"Location": "/b"}, b""),
            "https://www.bcr.ro/b": (302, {"Location": "https://cdn.bcr.ro/t.pdf"}, b""),
            "https://cdn.bcr.ro/t.pdf": (200, {"Content-Type": "application/pdf"}, b"%PDF-1.7 x")},
            follow_redirects=True)                       # cerut de apelant: se ignoră, se urmează de mână
        self.assertEqual((r.status_code, r.content, str(r.url)), (200, b"%PDF-1.7 x", "https://cdn.bcr.ro/t.pdf"))
        self.assertEqual(self.cereri, ["https://www.bcr.ro/a", "https://www.bcr.ro/b", "https://cdn.bcr.ro/t.pdf"])

    def test_corp_comprimat_se_decomprima_o_singura_data(self):
        r = self.adu("https://www.bcr.ro/gz", {"https://www.bcr.ro/gz": (
            200, {"Content-Type": "text/html", "Content-Encoding": "gzip"}, gzip.compress(PAGINA))})
        self.assertEqual(r.content, PAGINA)

    def test_al_doilea_pas_spre_retea_interna(self):
        for tinta in ("http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:8765/api/sumar",
                      "https://intern.bcr.ro/x", "http://[::ffff:10.0.0.1]/", "http://100.64.0.1/"):
            self.cereri.clear()
            with self.assertRaises(fh.AccesRefuzat, msg=tinta):
                self.adu("https://www.bcr.ro/a", {
                    "https://www.bcr.ro/a": (302, {"Location": "https://cdn.bcr.ro/b"}, b""),
                    "https://cdn.bcr.ro/b": (302, {"Location": tinta}, b"")})
            self.assertEqual(self.cereri, ["https://www.bcr.ro/a", "https://cdn.bcr.ro/b"], tinta)

    def test_adresa_de_plecare_interna_nu_se_cere(self):
        for url in ("https://intern.bcr.ro/x", "http://192.168.1.1/", "http://[::1]/", "file:///etc/passwd"):
            with self.assertRaises(fh.AccesRefuzat, msg=url):
                self.adu(url, {})
        self.assertEqual(self.cereri, [])

    def test_robots_si_blocat(self):
        with self.assertRaises(fh.AccesRefuzat) as ctx:
            self.adu("https://interzis.bcr.ro/pagina", {})
        self.assertIn("robots.txt", str(ctx.exception))
        with self.assertRaises(fh.AccesRefuzat):          # pe un pas de redirect
            self.adu("https://www.bcr.ro/a", {
                "https://www.bcr.ro/a": (302, {"Location": "https://interzis.bcr.ro/p"}, b"")})
        # robots.txt însuși se cere mereu (RFC 9309)
        self.assertEqual(self.adu("https://interzis.bcr.ro/robots.txt", {
            "https://interzis.bcr.ro/robots.txt": (200, {}, b"User-agent: *\nDisallow: /\n")}).status_code, 200)
        flux.marcheaza_blocat("https://www.bcr.ro/", "403 WAF", "bcr")
        with self.assertRaises(fh.AccesRefuzat) as ctx:
            self.adu("https://www.bcr.ro/alta", {})
        self.assertIn("BLOCAT", str(ctx.exception))
        self.assertEqual(self.cereri, ["https://www.bcr.ro/a", "https://interzis.bcr.ro/robots.txt"])

    def test_plafon(self):
        mare = b"%PDF-1.7 " + b"x" * 10_000
        with mock.patch.object(fh, "MAX_OCTETI", 4096):
            with self.assertRaises(fh.RaspunsPreaMare):          # fără Content-Length: numărat la citire
                self.adu("https://cdn.bcr.ro/a.pdf", {"https://cdn.bcr.ro/a.pdf": (200, {}, mare)})
            with self.assertRaises(fh.RaspunsPreaMare):          # gzip care se umflă peste plafon
                self.adu("https://cdn.bcr.ro/b.pdf", {"https://cdn.bcr.ro/b.pdf": (
                    200, {"Content-Encoding": "gzip"}, gzip.compress(b"\0" * 100_000))})

    def test_prea_multe_redirecturi(self):
        with self.assertRaises(httpx.TooManyRedirects):
            self.adu("https://www.bcr.ro/x", {"https://www.bcr.ro/x": (302, {"Location": "/x"}, b"")})
        self.assertEqual(len(self.cereri), fh._transport_mip().MAX_PASI_REDIRECT + 1)


class TestFiltruSurse(unittest.TestCase):
    BANCA = {"id": "bcr", "nume": "BCR", "url": "https://www.bcr.ro/", "domenii_inrudite": ["erstegroup.com"]}

    def filtreaza(self, urluri, deschise=(), texte=None):
        surse = [{"url": u, "citat": "x"} for u in urluri]
        with mock.patch("sys.stderr", new_callable=io.StringIO) as jurnal:
            pastrate = T.filtreaza_surse(surse, list(deschise), texte or {}, self.BANCA)
        return [s["url"] for s in pastrate], jurnal.getvalue()

    def test_pe_domeniu_sau_deschisa_ramane(self):
        urluri = ["https://www.bcr.ro/depozite", "https://cdn.bcr.ro/tarife.pdf", "http://bcr.ro/x",
                  "https://www.erstegroup.com/doc.pdf", "https://alt-site.ro/pagina/"]
        pastrate, jurnal = self.filtreaza(urluri, deschise=["https://alt-site.ro/pagina"])
        self.assertEqual(pastrate, urluri)
        self.assertEqual(jurnal, "")

    def test_scoase_cu_motiv_in_jurnal(self):
        rele = ["javascript:alert(1)", "file:///C:/Windows/win.ini", "ftp://bcr.ro/a.pdf",
                "https://evil.ro/bcr.ro", "https://bcr.ro.evil.ro/", "https://evil.ro\\@www.bcr.ro/",
                "https://www.bcr.ro@evil.ro/", "http://169.254.169.254/latest/meta-data/", "http://[::1/",
                None, 42]
        pastrate, jurnal = self.filtreaza(rele + ["https://www.bcr.ro/ok"])
        self.assertEqual(pastrate, ["https://www.bcr.ro/ok"])
        self.assertEqual(jurnal.count("sursă scoasă"), len(rele))
        self.assertIn("evil.ro", jurnal)

    def test_texte_conteaza_ca_deschise(self):
        pastrate, _ = self.filtreaza(["https://alt-site.ro/p"], texte={"https://alt-site.ro/p/": "text"})
        self.assertEqual(pastrate, ["https://alt-site.ro/p"])


class TestScriereSurseLibra(unittest.TestCase):
    """descopera_surse_libra.un_produs: ce scoate filtrul nu ajunge în surse_libra."""

    def test_un_produs(self):
        import descopera_surse_libra as D
        banca = {"id": "bcr", "nume": "BCR", "url": "https://www.bcr.ro/"}
        p = {"id": 7, "cod": "DEPOZIT_TERMEN", "denumire": "Depozit la termen", "segment": "PF",
             "descriere": "depozit"}
        citat = "dobânda la depozitul în lei pe 12 luni este 5,5% pe an"
        rez = {"surse": [
            {"url": "https://www.bcr.ro/depozite", "tip": "html", "rol": "pagina_produs", "citat": citat,
             "incredere": 0.9},
            {"url": "http://10.0.0.5/admin", "tip": "html", "rol": "pagina_produs", "citat": citat,
             "incredere": 0.95},
            {"url": "javascript:alert(1)", "tip": "html", "rol": "pagina_produs", "citat": citat,
             "incredere": 0.99}],
            "_deschise": ["https://www.bcr.ro/depozite"], "_texte": {"https://www.bcr.ro/depozite": citat},
            "_usage": {}}
        scrise = []
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(D, "IESIRE", Path(d)), \
                mock.patch.object(D.T, "ruleaza", return_value=rez), \
                mock.patch.object(D, "scrie_db", lambda idb, idp, surse, gol=None: scrise.extend(surse)), \
                mock.patch("sys.stderr", new_callable=io.StringIO):
            iesire = D.un_produs(banca, 1, p)
        self.assertEqual([s["url"] for s in iesire["surse"]], ["https://www.bcr.ro/depozite"])
        self.assertEqual([s["url"] for s in scrise], ["https://www.bcr.ro/depozite"])


class TestApelanti(Izolat):
    """Apelanții lui `adu_http` tratează refuzul ca pe un 403, nu ca pe o cădere."""

    def test_descarca_intoarce_refuzul(self):
        S = _modul("search_data_by_source", "search_data_by_source.py")
        with mock.patch.object(S.fh, "refuz_mip", mock.AsyncMock(return_value="interzis de robots.txt")):
            octeti, refuz = asyncio.run(S.descarca("https://www.bcr.ro/x", "http"))
        self.assertEqual((octeti, refuz), (b"", "interzis de robots.txt"))

    def test_candidati_refuz_la_cerere_e_blocat(self):
        import candidati_produse as C
        with mock.patch.object(C.fh, "refuz_mip", mock.AsyncMock(return_value="origine BLOCAT: 403")):
            with self.assertRaises(C.Blocat):
                asyncio.run(C.adu("https://www.bcr.ro/x"))
            # la verificarea robots, aceeași adresă e doar sărită
            rb = C.Robots()
            with mock.patch.object(C, "adu", mock.AsyncMock(return_value=types.SimpleNamespace(
                    status_code=404, text=""))):
                self.assertFalse(asyncio.run(rb.permis("https://www.bcr.ro/x")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
