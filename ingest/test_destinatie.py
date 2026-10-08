# ingest/test_destinatie.py
"""Garda de rețea internă (`destinatie.verifica`), fără DNS real: rezolvitorul e injectat."""
import os
import socket
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import destinatie as D  # noqa: E402


def rezolvitor(*ipuri):
    def rezolva(gazda, port, *a, **kw):
        if not ipuri:
            raise socket.gaierror(11001, "getaddrinfo failed")
        return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))
                for ip in ipuri]
    return rezolva


def nu_rezolva(*a, **kw):
    raise AssertionError("un IP literal nu se rezolvă")


class TestGarda(unittest.TestCase):
    def refuzat(self, url, rezolvitor=nu_rezolva):
        with self.assertRaises(D.DestinatieInterzisa, msg=url):
            D.verifica(url, rezolvitor)

    def test_ip_literal_care_nu_e_public(self):
        for url in ("http://127.0.0.1/", "http://127.1.2.3:8765/api/sumar", "https://10.1.2.3/x.pdf",
                    "http://172.16.0.10/", "http://172.31.255.1/", "http://192.168.1.1/",
                    "http://169.254.169.254/latest/meta-data/", "http://[::1]/", "http://[::ffff:127.0.0.1]/",
                    "http://[::ffff:10.0.0.1]:80/", "http://100.64.0.1/", "http://100.127.255.254/",
                    "http://0.0.0.0/", "http://[::]/", "http://224.0.0.1/", "http://[ff02::1]/",
                    "http://[fe80::1]/", "http://[fc00::1]/", "http://[64:ff9b::7f00:1]/",
                    "http://255.255.255.255/", "http://198.18.0.1/"):
            self.refuzat(url)

    def test_nume_care_duce_intern(self):
        for ip in ("127.0.0.1", "10.0.0.5", "172.16.4.4", "192.168.0.10", "169.254.169.254", "::1",
                   "::ffff:127.0.0.1", "100.64.1.1", "0.0.0.0"):
            self.refuzat("https://documente.banca.ro/tarife.pdf", rezolvitor(ip))

    def test_oricare_adresa_interna_refuza_tot_numele(self):
        self.refuzat("https://cdn.banca.ro/a.pdf", rezolvitor("93.184.216.34", "10.0.0.1"))

    def test_public_trece(self):
        D.verifica("https://8.8.8.8/x", nu_rezolva)
        D.verifica("http://[2606:4700::1111]/", nu_rezolva)
        D.verifica("https://www.bcr.ro/ro/persoane-fizice", rezolvitor("18.239.50.125"))
        D.verifica("https://www.ing.ro:443/doc.pdf", rezolvitor("2a02:2f0c::1", "93.184.216.34"))
        D.verifica("http://[::ffff:8.8.8.8]/", nu_rezolva)

    def test_doar_http_si_https(self):
        for url in ("file:///C:/Windows/win.ini", "ftp://banca.ro/a.pdf", "gopher://127.0.0.1:6379/_x",
                    "javascript:alert(1)", "//banca.ro/x", "banca.ro/x"):
            self.refuzat(url, rezolvitor("93.184.216.34"))

    def test_gazda_ambigua(self):
        # urllib citește gazda după ultimul „@”; alt client poate citi alta
        for url in ("http://banca.ro@127.0.0.1/", "http://banca.ro\\@127.0.0.1/", "http://a:b@banca.ro/",
                    "http://banca.ro 127.0.0.1/"):
            self.refuzat(url, rezolvitor("93.184.216.34"))
        self.refuzat("https://banca.ro:99999/", rezolvitor("93.184.216.34"))
        self.refuzat("http:///x", rezolvitor("93.184.216.34"))

    def test_nerezolvat_e_eroare_de_retea(self):
        with self.assertRaises(D.DestinatieNerezolvata):
            D.verifica("https://nu-exista.banca.ro/", rezolvitor())
        self.assertFalse(issubclass(D.DestinatieNerezolvata, D.DestinatieInterzisa))
        self.assertTrue(issubclass(D.DestinatieNerezolvata, OSError))

    def test_rezolvitorul_modulului_se_poate_inlocui(self):
        vechi = D.rezolva
        D.rezolva = rezolvitor("192.168.5.5")
        try:
            with self.assertRaises(D.DestinatieInterzisa):
                D.verifica("https://www.banca.ro/")
        finally:
            D.rezolva = vechi


if __name__ == "__main__":
    unittest.main()
