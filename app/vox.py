"""Vox (pagina #/vox): o întrebare despre o valoare a unei bănci → parametrii
unei căutări în baza noastră.

Modelul doar înțelege întrebarea, nu răspunde el: întoarce un JSON cu schemă strictă (băncile,
conceptul, categoria, termenul), iar valorile vin din `observatii_curente` prin `celula()` din
server, aceeași funcție ca Sertar-ul din 2.1. Modelul nu vede nicio valoare și nu scrie nicio
cifră; spre Anthropic pleacă doar întrebarea, lista băncilor și lista conceptelor (date publice),
nimic din catalogul intern Libra. Singurul text al modelului care ajunge pe ecran e `clarificare`.

Activ NUMAI local, cu `MIP_PERMITE_VOX=1` și o cheie reală în `.env`. Rutele stau în spatele
logării AD (07.10.2026), dar istoricul conversațiilor e comun tuturor utilizatorilor, iar fiecare
întrebare costă: pe `mcc-test` rămâne oprit.
Modulul nu știe de HTTP și nici de SQL: serverul îi dă funcțiile de citire, ca la `rulari.py`.
"""

import datetime
import importlib.util
import json
import os
import re
import secrets
import threading

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_JURNAL = os.path.join(RADACINA, "loguri", "vox")
MAX_TOKENS = 400        # interpretarea are sub 200 de tokeni; marja e pentru `clarificare`
# SDK-ul reîncearcă singur după timeout: cu 30 s și max_retries=2, „n-a răspuns în 30 s” venea
# după până la 90 s; acum cel mult 2 × 20 s, iar mesajul spune toată așteptarea
TIMEOUT_S = 20.0
REINCERCARI = 1


def _incarca_preturi():
    # tabelul de prețuri al fluxului de comparație, un singur loc; încărcat după cale, nu prin
    # sys.path, ca modulele din extragere_produse_bancare/ să nu acopere modulele din app/ și ingest/
    spec = importlib.util.spec_from_file_location(
        "preturi", os.path.join(RADACINA, "extragere_produse_bancare", "preturi.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


preturi = _incarca_preturi()

MODEL_IMPLICIT = "claude-haiku-4-5"    # ales de Nicolae pe 06.10.2026; MIP_VOX_MODEL îl schimbă
# `npm run dev`: pagina e pe :5173; proxy-ul Vite rescrie Host-ul la server, dar Origin rămâne
# http://localhost:5173 (vezi rulari.verifica_cerere, `porturi_extra`)
PORT_VITE = 5173
LUNGIME_MAX = 500
MAX_BANCI = 3
# BCR are 1.253 de valori `transfer_credit` (baza mip, 06.10.2026): rezumatul le numără pe toate,
# dar răspunsul trimite cel mult atâtea rânduri; restul sunt în Sertar
MAX_RANDURI = 50
# PF primul: la BCR · administrare cont, 302 valori PJ, 234 PFA și 33 PF stăteau într-un singur interval,
# 0–1.200 lei (mip_merge, 07.10.2026); rândurile fără segment în sursă vin la final. `celula` din server
# acceptă la `segment` doar aceste valori, plus `nemarcat`.
ORDINE_SEGMENT = ("pf", "pfa", "imm", "pj")
TIPURI = ("cautare", "neclar", "in_afara")
CHEI = ("tip", "banci", "concept", "categorie", "termen", "produs_credit", "text_cautat", "clarificare")
# Istoricul conversațiilor (coloana „Conversații” din pagina Vox): fișiere pe laptop, nu în bază
ID_CONVERSATIE = re.compile(r"[0-9a-f]{16}")
TITLU_MAX = 120
CONVERSATIE_LIPSA = "Conversația nu mai există."


class Respins(Exception):
    """Cerere greșită (400): întrebare goală sau prea lungă, interpretare anterioară invalidă."""


class EroareModel(Exception):
    """Apelul la model n-a reușit (502); mesajul e pentru utilizator."""


class ConversatieLipsa(Exception):
    """Conversația cerută nu există (404): ștearsă sau un id greșit în adresă."""


def mesaj_eroare(exc):
    """Mesajul pentru utilizator, de la eroarea cea mai specifică la cea generală (retryable sau nu)."""
    import anthropic
    if isinstance(exc, anthropic.AuthenticationError):
        return "Cheia Anthropic e respinsă (401). Verifică ANTHROPIC_API_KEY din .env."
    if isinstance(exc, anthropic.RateLimitError):
        return "Prea multe cereri la Anthropic (429). Încearcă din nou peste un minut."
    if isinstance(exc, anthropic.APITimeoutError):
        return f"Modelul n-a răspuns în {int(TIMEOUT_S * (REINCERCARI + 1))} s. Încearcă din nou."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Nu s-a putut ajunge la api.anthropic.com (rețea sau proxy)."
    if isinstance(exc, anthropic.APIStatusError):
        return f"API-ul Anthropic a răspuns cu eroarea {exc.status_code}."
    return f"Eroare la apelul modelului ({exc.__class__.__name__})."


def _acum():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _gol(tip="neclar"):
    return {"tip": tip, "banci": [], "concept": None, "categorie": None, "termen": None,
            "produs_credit": None, "text_cautat": None, "clarificare": None}


def cheie_reala():
    """Pe 06.10.2026, `.env`-ul din rădăcină avea în ANTHROPIC_API_KEY un placeholder de 10
    caractere (jobul 172); cheia reală pusă atunci începe cu `sk-ant-` și are 108. Pragul de 40
    desparte orice placeholder scurt de o cheie, fără să depindă de lungimea exactă a cheilor."""
    k = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return k.startswith("sk-ant-") and len(k) >= 40


def activ():
    return os.environ.get("MIP_PERMITE_VOX", "").strip() == "1" and cheie_reala()


def model():
    return os.environ.get("MIP_VOX_MODEL", "").strip() or MODEL_IMPLICIT


def verifica_intrebarea(intrebare):
    if not isinstance(intrebare, str) or not intrebare.strip():
        raise Respins("Scrie o întrebare.")
    intrebare = intrebare.strip()
    if len(intrebare) > LUNGIME_MAX:
        raise Respins(f"Întrebarea are peste {LUNGIME_MAX} de caractere.")
    return intrebare


def verifica_anterior(anterior):
    """Interpretarea întrebării precedente, trimisă de pagină pentru „și la BRD?”. Ajunge la model
    doar ca text de context, deci se verifică forma și mărimea, nu și listele."""
    if anterior is None:
        return None
    if not isinstance(anterior, dict) or not set(anterior) <= set(CHEI):
        raise Respins("Interpretarea anterioară nu e validă.")
    curat = {k: anterior.get(k) for k in CHEI}
    if len(json.dumps(curat, ensure_ascii=False)) > 1000:
        raise Respins("Interpretarea anterioară nu e validă.")
    return curat


def schema(ctx):
    """Schema strictă a răspunsului: băncile și conceptele sunt `enum` generate din bază, deci API-ul
    nu acceptă un slug inexistent. Modul strict nu acceptă `maxItems`: limita de 3 bănci e în
    `valideaza`."""
    def optional(valori):
        return {"anyOf": [{"type": "string", "enum": list(valori)}, {"type": "null"}]}

    text_optional = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    return {
        "type": "object",
        "properties": {
            "tip": {"type": "string", "enum": list(TIPURI)},
            "banci": {"type": "array", "items": {"type": "string", "enum": [b["slug"] for b in ctx["banci"]]}},
            "concept": optional(c["camp"] for c in ctx["concepte"]),
            "categorie": optional(ctx["categorii"]),
            "termen": optional(ctx["termene"]),
            "produs_credit": optional(ctx["produse"]),
            "text_cautat": text_optional,
            "clarificare": text_optional,
        },
        "required": list(CHEI),
        "additionalProperties": False,
    }


def prompt(ctx):
    """Promptul de sistem, construit din bază. Identic între întrebări (fără dată, fără ordine
    aleatoare): cache-ul promptului cere un prefix stabil."""
    linii = [
        "Ești interpretul paginii Vox din Marketing Command Center (Libra Bank).",
        "Utilizatorul întreabă, în română sau în engleză, despre o valoare publicată de o bancă din "
        "România: un comision, o dobândă, o limită.",
        "Sarcina ta: traduci întrebarea în parametrii unei căutări în baza noastră. NU răspunzi la "
        "întrebare, nu scrii nicio cifră și nu folosești ce știi despre bănci: valorile le arată "
        "aplicația, din bază.",
        "",
        "Reguli:",
        "- tip = cautare: întrebarea cere o valoare a uneia sau mai multor bănci (cel mult 3).",
        "- tip = neclar: lipsește banca sau nu se înțelege ce valoare; scrie atunci în clarificare "
        "o întrebare scurtă, în limba utilizatorului.",
        "- tip = in_afara: orice altceva (clasamente de tipul „cine are cel mai mic…”, aplicații, "
        "recenzii, campanii, sfaturi, texte de scris, întrebări generale).",
        "- concept: conceptul din lista de mai jos care corespunde valorii cerute. Dacă niciunul nu "
        "se potrivește clar, concept = null și scrii în text_cautat 1–3 cuvinte în română, așa cum ar "
        "apărea în tariful băncii (de pildă „datoria vamală”). Nu forța un concept.",
        "- Când banca și serviciul sunt clare, tip = cautare, chiar dacă serviciul nu are concept și "
        "nu-l recunoști: aplicația caută text_cautat în tarifele băncii, iar tu nu știi ce conțin "
        "tarifele, deci nu pune neclar pentru că nu ești sigur că serviciul există.",
        "- categorie: doar la dobânzi (depozite, credite, conturi și carduri); la comisioane, null. "
        "La o dobândă, conceptul e unul din cele ale categoriei (lista „Categorii” de la final); "
        "„dobânda” fără alt detaliu e `nominala`.",
        "- Termenii englezești au conceptul lor, nu pe cel mai apropiat: APR / annual percentage rate "
        "= `dae` (nu `nominala`; „interest rate” e `nominala`); incoming payment / incoming transfer "
        "= `incasare` (bani primiți), outgoing transfer / payment sent = `transfer_credit` (bani trimiși).",
        "- termen și produs_credit: doar dacă întrebarea le spune.",
        "- Dacă primești interpretarea întrebării anterioare, întrebarea curentă o poate continua "
        "(„și la BRD?”, „dar pe 6 luni?”): păstrezi ce nu se schimbă. O bancă numită în continuare "
        "(„și la BRD?”) înlocuiește băncile anterioare, nu se adaugă la ele.",
        "",
        "Băncile (slug: nume):",
    ]
    linii += [f"{b['slug']}: {b['nume']}" for b in ctx["banci"]]
    linii += ["", "Conceptele (slug · unități · categorii · câte valori · denumiri reale din tarifele băncilor):"]
    for c in ctx["concepte"]:
        exemple = " | ".join(e[:80] for e in c["exemple"])
        linii.append(f"{c['camp']} · {', '.join(c['unitati'])} · {', '.join(c['categorii'])} · {c['n']} · {exemple}")
    linii += [
        "",
        "Categorii: " + "; ".join(
            f"{k} ({v}; concepte: {', '.join(ctx['concepte_categorie'].get(k, []))})"
            for k, v in ctx["categorii"].items()),
        "Termene: " + "; ".join(f"{k} ({v})" for k, v in ctx["termene"].items()),
        "Tipuri de credit: " + "; ".join(f"{k} ({v})" for k, v in ctx["produse"].items()),
    ]
    return "\n".join(linii)


# Fără diacritice pe ambele părți: întrebarea vine adesea scrisă fără ele, tarifele cu ele.
# Aceleași litere ca `_TEXT_CAUTARE` din server, care face același lucru în SQL.
DIACRITICE = str.maketrans("ăâîșşțţ", "aaisstt")


def cuvinte_cautare(text):
    """Cuvintele unei căutări după text: litere și cifre (fără `%` sau `_`, care în LIKE ar fi
    wildcard-uri), de cel puțin 3 caractere, fără dubluri, cel mult 5. Aici, nu în server: și
    validarea, și `celula` trebuie să știe dacă rămâne ceva de căutat.

    Fiecare cuvânt e tăiat la rădăcină (6+ litere pierd ultimele 2, 5 litere ultima): pe subșirul
    exact, „datoria vamală” nu găsea „Decontarea electronică a datoriei vamale” la BCR (0 rânduri
    din 13, mip, 06.10.2026); flexiunea românească schimbă tocmai finalul cuvântului."""
    cuvinte = []
    for c in re.findall(r"[^\W_]+", (text or "").lower().translate(DIACRITICE)):
        if len(c) < 3:
            continue
        if not c.isdigit():     # „100000” tăiat la „1000” ar potrivi orice sumă care îl conține
            c = c[:-2] if len(c) >= 6 else c[:-1] if len(c) == 5 else c
        if c not in cuvinte:
            cuvinte.append(c)
    return cuvinte[:5]


def _text(v, maxim):
    if not isinstance(v, str):
        return None
    return v.strip()[:maxim] or None


def valideaza(brut, ctx):
    """Interpretarea curată și băncile tăiate peste limită.

    Schema strictă oprește deja la API un slug inexistent; verificarea se repetă aici fiindcă un
    model schimbat din `.env` sau un răspuns tăiat n-ar trebui să ajungă într-o interogare. Ce nu e
    din liste devine `neclar` fără clarificare: pagina arată atunci mesajul ei fix, nu textul modelului.
    """
    if not isinstance(brut, dict) or brut.get("tip") not in TIPURI:
        return _gol(), []
    banci = brut.get("banci")
    if not isinstance(banci, list) or any(b not in {x["slug"] for x in ctx["banci"]} for b in banci):
        return _gol(), []
    permise = {"concept": {c["camp"] for c in ctx["concepte"]}, "categorie": set(ctx["categorii"]),
               "termen": set(ctx["termene"]), "produs_credit": set(ctx["produse"])}
    for cheie, valori in permise.items():
        if brut.get(cheie) is not None and brut.get(cheie) not in valori:
            return _gol(), []
    banci = list(dict.fromkeys(banci))
    curat = _gol(brut["tip"])
    curat.update({k: brut.get(k) for k in permise})
    curat["banci"] = banci[:MAX_BANCI]
    curat["text_cautat"] = _text(brut.get("text_cautat"), 80)
    if not cuvinte_cautare(curat["text_cautat"]):
        # „PO” nu are niciun cuvânt de căutat: fișa ar fi spus „nu avem valori” fără să caute
        curat["text_cautat"] = None
    curat["clarificare"] = _text(brut.get("clarificare"), 300)
    # categoria doar unde conceptul are valori: `administrare_cont` e numai sub `comision`, iar o
    # categorie din 2.2 lângă el golea fișa („BCR n-are comisionul”, deși avea 570 de valori)
    categorii = next((c["categorii"] for c in ctx["concepte"] if c["camp"] == curat["concept"]), [])
    if curat["categorie"] not in categorii:
        curat["categorie"] = None
    cu_ce = bool(curat["banci"] and (curat["concept"] or curat["text_cautat"]))
    if curat["tip"] == "cautare" and not cu_ce:
        curat["tip"] = "neclar"
    elif curat["tip"] == "neclar" and cu_ce:
        # cu bancă și valoare nu e neclar (spec); Haiku punea neclar pe servicii fără concept, cu o
        # clarificare care afirma că serviciul „nu se găsește în tarife”, fals (evaluarea, 06.10.2026)
        curat["tip"], curat["clarificare"] = "cautare", None
    return curat, banci[MAX_BANCI:]


def _categorie(r):
    return (r.get("cod_scenariu") or "").split("|")[0]


# „gratuit” are sens doar la comisioane: pe mip erau 21 de dobânzi neambigue de 0% (06.10.2026),
# iar „2 gratuite” lângă o dobândă la card s-ar citi ca un comision
CATEGORII_COMISION = ("comision", "comisioane")


def _ordine_segment(segment):
    return ORDINE_SEGMENT.index(segment) if segment in ORDINE_SEGMENT else len(ORDINE_SEGMENT)


def rezuma(randuri):
    """Pe segment, unitate și categorie: câte valori, intervalul, câte gratuite; fără cele ambigue, ca în Sertar.

    Pe categorie, nu doar pe unitate: `nominala` e și dobânda de depozit, și cea de credit, iar fără
    categorie în întrebare un singur interval le-ar amesteca (6,5% la depozit cu 9,9% la ipotecar).
    Pe segment, cu PF primul (`ORDINE_SEGMENT`); un rând fără segment în sursă are grupa lui, la final.
    """
    grupe = {}
    for r in randuri:
        v = r.get("valoare")
        if r.get("ambiguu") or v is None:
            continue
        cheie = (r.get("segment"), r.get("unitate") or "", _categorie(r))
        g = grupe.setdefault(cheie, {"segment": cheie[0], "unitate": cheie[1], "categorie": cheie[2],
                                     "n": 0, "minim": v, "maxim": v, "gratuite": 0})
        g["n"] += 1
        g["minim"] = min(g["minim"], v)
        g["maxim"] = max(g["maxim"], v)
        g["gratuite"] += int(v == 0 and cheie[2] in CATEGORII_COMISION)
    return sorted(grupe.values(),
                  key=lambda g: (_ordine_segment(g["segment"]), -g["n"], g["categorie"], g["unitate"]))


def _moment(data):
    """Ora unei ture, pentru ordonare: după ora reală, nu după text (la ora de iarnă „03:10+02:00” e
    după „03:30+03:00”); o dată stricată ajunge la coadă."""
    try:
        return datetime.datetime.fromisoformat(data).timestamp()
    except (TypeError, ValueError):
        return float("-inf")


class Istoric:
    """Conversațiile din Vox: câte un fișier JSONL pe conversație, în `dir` (pe laptop, nu în bază).

    Un rând pe întrebare (`{data, intrebare, raspuns}`) sau pe redenumire (`{data, titlu}`): fișierul
    doar crește, deci o scriere întreruptă strică cel mult ultimul rând, care se sare la citire. Orice
    id venit din afară trece prin `valid` înainte să devină cale, deci nu poate ieși din `dir`."""

    def __init__(self, dir):
        self.dir = dir
        self._lacat = threading.Lock()
        # id -> ((mtime_ns, mărime), rezumat): un răspuns are până la ~60 KB, iar lista se cere după
        # fiecare întrebare; un fișier neschimbat nu se recitește
        self._rezumate = {}

    @staticmethod
    def valid(id):
        return isinstance(id, str) and ID_CONVERSATIE.fullmatch(id) is not None

    @staticmethod
    def id_nou():
        return secrets.token_hex(8)

    def _cale(self, id):
        return os.path.join(self.dir, id + ".jsonl")

    def exista(self, id):
        return self.valid(id) and os.path.isfile(self._cale(id))

    def _scrie(self, id, rand):
        os.makedirs(self.dir, exist_ok=True)
        with self._lacat:
            with open(self._cale(id), "a", encoding="utf-8") as f:
                f.write(json.dumps(rand, ensure_ascii=False, default=str) + "\n")

    def adauga(self, id, intrebare, raspuns, data=None):
        if not self.valid(id):
            raise ConversatieLipsa(CONVERSATIE_LIPSA)
        self._scrie(id, {"data": data or _acum(), "intrebare": intrebare, "raspuns": raspuns})

    def citeste(self, id):
        """Conversația întreagă (`id`, `titlu`, `redenumita`, `ture`), sau None."""
        if not self.valid(id):
            return None
        try:
            # errors="replace": o scriere tăiată în mijlocul unei litere de 2 octeți („ă”) arunca
            # UnicodeDecodeError și lua cu ea toată lista; așa doar rândul acela nu mai e JSON și se sare
            with open(self._cale(id), encoding="utf-8", errors="replace") as f:
                linii = f.readlines()
        except OSError:
            return None
        ture, titlu = [], None
        for linie in linii:
            try:
                r = json.loads(linie)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            if isinstance(r.get("intrebare"), str):
                ture.append({"data": r.get("data"), "intrebare": r["intrebare"], "raspuns": r.get("raspuns")})
            elif "titlu" in r:
                titlu = r["titlu"] if isinstance(r["titlu"], str) and r["titlu"] else None
        if not ture:
            return None
        return {"id": id, "titlu": titlu or ture[0]["intrebare"], "redenumita": titlu is not None, "ture": ture}

    def _rezumat(self, id):
        st = os.stat(self._cale(id))
        cheie = (st.st_mtime_ns, st.st_size)
        vechi = self._rezumate.get(id)
        if vechi and vechi[0] == cheie:
            return vechi[1]
        c = self.citeste(id)
        rez = None if c is None else {
            "id": id, "titlu": c["titlu"], "redenumita": c["redenumita"], "intrebari": len(c["ture"]),
            "texte": [t["intrebare"] for t in c["ture"]],
            "inceputa": c["ture"][0]["data"], "ultima": c["ture"][-1]["data"],
            "cost_usd": sum((t["raspuns"].get("cost_usd") or 0) if isinstance(t["raspuns"], dict) else 0
                            for t in c["ture"]),
        }
        self._rezumate[id] = (cheie, rez)
        return rez

    def lista(self):
        """Rezumatele, cea cu ultima întrebare cea mai recentă prima."""
        try:
            nume = os.listdir(self.dir)
        except OSError:
            return []
        rez = []
        for n in nume:
            id = n[:-6] if n.endswith(".jsonl") else None
            if not self.valid(id):
                continue
            try:
                r = self._rezumat(id)
            except OSError:
                continue
            if r:
                rez.append(r)
        return sorted(rez, key=lambda r: _moment(r["ultima"]), reverse=True)

    def redenumeste(self, id, titlu):
        """Un rând `{data, titlu}` în plus; gol = înapoi la prima întrebare. Întoarce titlul afișat."""
        if titlu is not None and not isinstance(titlu, str):
            raise Respins("Titlul nu e valid.")
        titlu = (titlu or "").strip()
        if len(titlu) > TITLU_MAX:
            raise Respins(f"Titlul are peste {TITLU_MAX} de caractere.")
        if not self.exista(id):
            raise ConversatieLipsa(CONVERSATIE_LIPSA)
        self._scrie(id, {"data": _acum(), "titlu": titlu or None})
        c = self.citeste(id)
        return {"titlu": c["titlu"], "redenumita": c["redenumita"]}

    def sterge(self, id):
        if not self.exista(id):
            return False
        try:
            with self._lacat:
                os.remove(self._cale(id))
        except FileNotFoundError:
            return False
        self._rezumate.pop(id, None)
        return True


class Vox:
    """O întrebare → interpretarea modelului → valorile din bază. Fără HTTP și fără SQL: serverul
    dă funcțiile de citire (`context`, `cauta`, `stare_banca`), ca la `rulari.Rulari`."""

    def __init__(self, context, cauta, stare_banca, client=None, dir_jurnal=DIR_JURNAL, dir_conversatii=None):
        self._sursa_context = context
        self._cauta = cauta
        self._stare_banca = stare_banca
        self._client = client
        self.dir = dir_jurnal
        # lângă jurnal: în teste și la evaluare jurnalul e într-un dosar temporar, deci și conversațiile
        self.istoric = Istoric(dir_conversatii or os.path.join(dir_jurnal, "conversatii"))
        # separat de tokenul rulărilor: pagina asta are voie și de pe Vite (:5173), rulările nu
        self.token = secrets.token_urlsafe(32)
        self._lacat = threading.Lock()
        self._lacat_jurnal = threading.Lock()
        self._pregatit = None

    def stare(self):
        return {"activ": activ(), "model": model()}

    def _context(self):
        # o conexiune nouă la Postgres costă ~2 s pe Windows, iar promptul trebuie să rămână identic
        # între întrebări ca să intre în cache: se construiește o dată, la prima întrebare; după o
        # încărcare de date nouă se reface la repornirea serverului
        with self._lacat:
            if self._pregatit is None:
                ctx = self._sursa_context()
                self._pregatit = (ctx, prompt(ctx), schema(ctx))
            return self._pregatit

    def _clientul(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(timeout=TIMEOUT_S, max_retries=REINCERCARI)
        return self._client

    def _cheama(self, m, sistem, sch, intrebare, anterior):
        import anthropic
        continut = intrebare if anterior is None else (
            "Interpretarea întrebării anterioare: " + json.dumps(anterior, ensure_ascii=False)
            + "\nÎntrebarea curentă: " + intrebare)
        try:
            r = self._clientul().messages.create(
                model=m,
                max_tokens=MAX_TOKENS,
                system=[{"type": "text", "text": sistem, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": continut}],
                output_config={"format": {"type": "json_schema", "schema": sch}},
            )
        except anthropic.APIError as exc:
            raise EroareModel(mesaj_eroare(exc)) from None
        tokeni = preturi.aduna_usage({}, r.usage)
        tokeni.pop("apeluri", None)
        text = next((b.text for b in r.content if getattr(b, "type", None) == "text"), "")
        try:
            brut = json.loads(text)
        except ValueError:
            brut = None
        return brut, tokeni, r.stop_reason

    def _raspuns(self, banca, interp):
        text = None if interp["concept"] else interp["text_cautat"]

        def cauta(termen, produs):
            return self._cauta(banca, interp["concept"], interp["categorie"], termen, produs, text)

        termen, produs = interp["termen"], interp["produs_credit"]
        randuri, relaxate = cauta(termen, produs), []
        # termenul și tipul de credit se citesc din textul băncii, deci pot goli un răspuns: la „depozit
        # pe 12 luni” 28 din 30 de bănci n-aveau nicio valoare, deși Libra avea 11 dobânzi fără termen în
        # sursă (mip_merge, 07.10.2026). Se cade pe „termen nespecificat”, apoi și pe „credit
        # nespecificat”, nu pe niciun filtru: BCR are 6% pe 5 luni, răspuns greșit la „12 luni”
        if not randuri and termen and termen != "necunoscut":
            termen, relaxate = "necunoscut", ["termen"]
            randuri = cauta(termen, produs)
        if not randuri and produs and produs != "altele":
            produs, relaxate = "altele", relaxate + ["produs"]
            randuri = cauta(termen, produs)
        fara_filtre = None
        if not randuri:
            relaxate = []
            # nici așa: câte sunt fără niciun filtru (alt termen, alt tip de credit), ca „nu avem
            # valori” să nu se citească „banca n-are produsul”
            if interp["termen"] or interp["produs_credit"]:
                fara_filtre = len(cauta(None, None))
        # PF primele, înainte de tăierea la MAX_RANDURI: la BCR · administrare cont primele 50 de rânduri
        # (ordinea pe serviciu) erau 18 PF, 19 PFA și 13 PJ amestecate (mip_merge, 07.10.2026)
        randuri = sorted(randuri, key=lambda r: _ordine_segment(r.get("segment")))
        lipsa = None if randuri else self._stare_banca(banca)
        return {
            "banca": banca,
            "mod": "text" if text else "concept",
            "total": len(randuri),
            # căutarea după text e tăiată la MAX_RANDURI în SQL, deci totalul real poate fi mai mare
            "limitat": bool(text) and len(randuri) >= MAX_RANDURI,
            "ambigue": sum(1 for r in randuri if r.get("ambiguu")),
            # rezumatul are doar valorile cu cifră; fără acest număr, „1 valoare” stătea deasupra unui
            # tabel mai lung (589 de valori doar text, neambigue, în mip_merge, 07.10.2026)
            "fara_cifra": sum(1 for r in randuri if r.get("valoare") is None and not r.get("ambiguu")),
            "rezumat": rezuma(randuri),
            "randuri": randuri[:MAX_RANDURI],
            "filtre_relaxate": relaxate,
            "stare_banca": lipsa["stare"] if lipsa else None,
            # câte surse ale băncii sunt blocate și de ce; doar când banca n-are nicio valoare
            "blocaje": {k: lipsa[k] for k in ("surse", "robots", "refuzate", "pdf")} if lipsa else None,
            "fara_filtre": fara_filtre,
        }

    def intreaba(self, intrebare, anterior=None, conversatie=None):
        intrebare = verifica_intrebarea(intrebare)
        anterior = verifica_anterior(anterior)
        if conversatie is not None and not self.istoric.exista(conversatie):
            # înainte de model: o conversație ștearsă în alt tab nu se mai plătește
            raise Respins(CONVERSATIE_LIPSA)
        ctx, sistem, sch = self._context()
        m = model()
        rand = {"data": _acum(), "intrebare": intrebare, "model": m, "conversatie": conversatie}
        try:
            brut, tokeni, stop = self._cheama(m, sistem, sch, intrebare, anterior)
        except EroareModel as exc:
            rand["eroare"] = str(exc)
            self._jurnal(rand)
            raise
        if stop in ("refusal", "max_tokens"):
            interp, ignorate = _gol(), []
        else:
            interp, ignorate = valideaza(brut, ctx)
        cost = preturi.cost(m, tokeni["intrare"], tokeni["iesire"], tokeni["citire_cache"], tokeni["scriere_cache"])
        rand.update(interpretare=interp, stop=stop, tokeni=tokeni, cost_usd=cost)
        try:
            raspunsuri = [self._raspuns(b, interp) for b in interp["banci"]] if interp["tip"] == "cautare" else []
        except Exception as exc:
            # apelul la model s-a plătit deja: întrebarea intră în jurnal și când cade baza
            rand["eroare"] = f"{exc.__class__.__name__}: {exc}"
            self._jurnal(rand)
            raise
        rand["randuri"] = {r["banca"]: r["total"] for r in raspunsuri}
        rezultat = {"interpretare": interp, "ignorate": ignorate, "raspunsuri": raspunsuri,
                    "model": m, "tokeni": tokeni, "cost_usd": cost}
        id = conversatie or self.istoric.id_nou()
        try:
            self.istoric.adauga(id, intrebare, rezultat)
        except OSError:
            # disc plin sau fără drept de scriere: răspunsul se arată oricum, doar nu se păstrează
            id = None
        rand["conversatie"] = id
        self._jurnal(rand)
        return {**rezultat, "conversatie": id}

    def _jurnal(self, rand):
        """Un rând pe întrebare, ca să se vadă unde greșește interpretarea. Nu oprește răspunsul."""
        try:
            os.makedirs(self.dir, exist_ok=True)
            with self._lacat_jurnal:
                with open(os.path.join(self.dir, rand["data"][:7] + ".jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rand, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass
