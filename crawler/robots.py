"""Conformitate robots.txt, cu potrivire de modele conform RFC 9309.

De ce nu folosim urllib.robotparser: acesta face doar potrivire pe prefix si ignora
wildcard-urile. ING, de exemplu, are "Disallow: *.pdf" — o regula pe care robotparser
nu ar prinde-o niciodata, si am fi descarcat documente interzise.

Implementam deci:
  - wildcard "*" si ancora de final "$"
  - precedenta pe cel mai lung model (Allow bate Disallow la egalitate)
  - RFC 9309: robots.txt cu cod 4xx => nicio restrictie declarata

robots.txt e citit prin browser, fiindca unele banci au WAF care respinge cereri
non-browser dar servesc fisierul normal unui browser (ex. Cetelem).
"""
import re
from urllib.parse import urljoin, urlparse

from .banci import CAI_INTERZISE


def _compileaza(model):
    """Transforma un model din robots.txt in regex (suporta * si $ final)."""
    if model.endswith("$"):
        corp, ancora = model[:-1], "$"
    else:
        corp, ancora = model, ""
    regex = "".join(".*" if c == "*" else re.escape(c) for c in corp)
    return re.compile("^" + regex + ancora)


class RegulliRobots:
    """Regulile robots.txt pentru un domeniu, aplicate grupului User-agent: *."""

    def __init__(self, banca_id, base_url, delay_implicit=2):
        self.banca_id = banca_id
        self.base_url = base_url
        self.delay = delay_implicit
        self.status = "necitit"
        self.reguli = []            # (lungime_model, permite, regex)
        self.sitemapuri = []
        # Textul brut se pastreaza ca dovada: verdictul "interzis" pentru un
        # document trebuie sa poata fi arătat, nu doar afirmat, iar regulile
        # compilate nu se mai citesc de om. Scriptul de salvare il scria pana
        # acum dintr-o variabila locala, deci originile verificate din alte
        # scripturi rămâneau fara dovada.
        self.text_brut = None
        self.cai_interzise = CAI_INTERZISE.get(banca_id, [])
        self._grup_stea = False     # grupul de user-agent curent include "*"

    # ------------------------------------------------------------------ citire
    def citeste(self, page, request_ctx=None):
        """Incarca robots.txt. Incearca doua canale, fiindca niciunul nu merge peste tot:

        1. cererea de tip API (corp brut, imun la randare si la descarcari automate —
           unele banci servesc robots.txt cu Content-Disposition: attachment, iar
           navigarea in pagina eseueaza cu "Download is starting");
        2. navigarea in pagina (functioneaza unde un WAF respinge cererile non-browser).
        """
        url = urljoin(self.base_url, "/robots.txt")
        text, cod, ultima_eroare = None, None, None

        if request_ctx is not None:
            try:
                resp = request_ctx.get(url, timeout=25000)
                cod = resp.status
                if 200 <= cod < 300:
                    candidat = resp.text()
                    if candidat and "user-agent" in candidat.lower():
                        text = candidat
            except Exception as e:
                ultima_eroare = str(e).splitlines()[0][:60]

        if text is None:
            try:
                resp = page.goto(url, timeout=25000)
                cod = resp.status if resp else cod
                if cod and 200 <= cod < 300:
                    # Corpul brut, NU inner_text: unele banci servesc robots.txt ca
                    # text/html, iar randarea colapseaza liniile si regulile devin
                    # neparsabile (am avut cazul BCR: 24 de reguli citite ca 0).
                    try:
                        text = resp.text()
                    except Exception:
                        text = None
                    if not text or "\n" not in text.strip():
                        try:
                            text = page.inner_text("body")
                        except Exception:
                            pass
            except Exception as e:
                ultima_eroare = str(e).splitlines()[0][:60]

        if text is None:
            if cod and not 200 <= cod < 300:
                # RFC 9309: 4xx => fara restrictii declarate
                self.status = f"inaccesibil (cod {cod}) - tratat ca fara restrictii"
            else:
                self.status = f"NECITIT ({ultima_eroare or 'necunoscut'})"
            return

        if "user-agent" not in text.lower():
            self.status = f"invalid (cod {cod}, continut non-robots)"
            return
        if "\n" not in text.strip() and text.lower().count("user-agent") > 1:
            self.status = f"necitibil (cod {cod}, linii colapsate)"
            return

        self.text_brut = text
        self._parseaza(text)
        self.status = f"citit (cod {cod}, {len(self.reguli)} reguli pentru *)"

    def _parseaza(self, text):
        in_grup_stea = False
        grup_curent_are_stea = False
        for linie_bruta in text.splitlines():
            linie = linie_bruta.split("#")[0].strip()
            if not linie:
                continue
            if ":" not in linie:
                continue
            cheie, _, valoare = linie.partition(":")
            cheie = cheie.strip().lower()
            valoare = valoare.strip()

            if cheie == "user-agent":
                # un grup poate lista mai multi agenti inainte de reguli
                if not in_grup_stea:
                    grup_curent_are_stea = False
                grup_curent_are_stea = grup_curent_are_stea or valoare == "*"
                in_grup_stea = True
                self._grup_stea = grup_curent_are_stea
                continue

            if cheie == "sitemap":
                self.sitemapuri.append(valoare)
                continue

            # orice alta directiva incheie enumerarea de user-agent
            in_grup_stea = False
            if not self._grup_stea:
                continue

            if cheie in ("disallow", "allow"):
                if cheie == "disallow" and valoare == "":
                    continue  # "Disallow:" gol = fara restrictie
                if valoare == "":
                    continue
                self.reguli.append(
                    (len(valoare), cheie == "allow", _compileaza(valoare)))
            elif cheie == "crawl-delay":
                try:
                    self.delay = max(self.delay, float(valoare))
                except ValueError:
                    pass

    # ---------------------------------------------------------------- aplicare
    def permite(self, url):
        """True daca URL-ul poate fi accesat conform regulilor grupului *."""
        for interzis in self.cai_interzise:
            if interzis in url:
                return False

        analiza = urlparse(url)
        cale = analiza.path or "/"
        if analiza.query:
            cale += "?" + analiza.query

        cel_mai_lung, permite = -1, True
        for lungime, este_allow, regex in self.reguli:
            if regex.match(cale):
                # cel mai lung model castiga; la egalitate, Allow bate Disallow
                if lungime > cel_mai_lung or (lungime == cel_mai_lung and este_allow):
                    cel_mai_lung, permite = lungime, este_allow
        return permite
