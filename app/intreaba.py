"""„Întreabă datele” (pagina #/intreaba): o întrebare despre o valoare a unei bănci → parametrii
unei căutări în baza noastră.

Modelul doar înțelege întrebarea, nu răspunde el: întoarce un JSON cu schemă strictă (băncile,
conceptul, categoria, termenul), iar valorile vin din `observatii_curente` prin `celula()` din
server, aceeași funcție ca Sertar-ul din 2.1. Modelul nu vede nicio valoare și nu scrie nicio
cifră; spre Anthropic pleacă doar întrebarea, lista băncilor și lista conceptelor (date publice),
nimic din catalogul intern Libra. Singurul text al modelului care ajunge pe ecran e `clarificare`.

Activ NUMAI local, cu `MIP_PERMITE_INTREBARI=1` și o cheie reală în `.env`: `mcc-test` n-are
autentificare (06.10.2026), iar cheia ar fi folosibilă de oricine din rețeaua internă.
Modulul nu știe de HTTP și nici de SQL: serverul îi dă funcțiile de citire, ca la `rulari.py`.
"""

import datetime
import importlib.util
import json
import os
import secrets
import threading

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_JURNAL = os.path.join(RADACINA, "loguri", "intreaba")
MAX_TOKENS = 400        # interpretarea are sub 200 de tokeni; marja e pentru `clarificare`
TIMEOUT_S = 30.0


def _incarca_preturi():
    # tabelul de prețuri al fluxului de comparație, un singur loc; încărcat după cale, nu prin
    # sys.path, ca modulele din extragere_produse_bancare/ să nu acopere modulele din app/ și ingest/
    spec = importlib.util.spec_from_file_location(
        "preturi", os.path.join(RADACINA, "extragere_produse_bancare", "preturi.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


preturi = _incarca_preturi()

MODEL_IMPLICIT = "claude-haiku-4-5"    # ales de Nicolae pe 06.10.2026; MIP_INTREABA_MODEL îl schimbă
# `npm run dev`: proxy-ul Vite (fără changeOrigin) păstrează Host-ul paginii, localhost:5173
PORT_VITE = 5173
LUNGIME_MAX = 500
MAX_BANCI = 3
# BCR are 1.253 de valori `transfer_credit` (baza mip, 06.10.2026): rezumatul le numără pe toate,
# dar răspunsul trimite cel mult atâtea rânduri; restul sunt în Sertar
MAX_RANDURI = 50
TIPURI = ("cautare", "neclar", "in_afara")
CHEI = ("tip", "banci", "concept", "categorie", "termen", "produs_credit", "text_cautat", "clarificare")


class Respins(Exception):
    """Cerere greșită (400): întrebare goală sau prea lungă, interpretare anterioară invalidă."""


class EroareModel(Exception):
    """Apelul la model n-a reușit (502); mesajul e pentru utilizator."""


def mesaj_eroare(exc):
    """Mesajul pentru utilizator, de la eroarea cea mai specifică la cea generală (retryable sau nu)."""
    import anthropic
    if isinstance(exc, anthropic.AuthenticationError):
        return "Cheia Anthropic e respinsă (401). Verifică ANTHROPIC_API_KEY din .env."
    if isinstance(exc, anthropic.RateLimitError):
        return "Prea multe cereri la Anthropic (429). Încearcă din nou peste un minut."
    if isinstance(exc, anthropic.APITimeoutError):
        return f"Modelul n-a răspuns în {int(TIMEOUT_S)} s. Încearcă din nou."
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
    caractere (jobul 172); o cheie reală începe cu `sk-ant-` și are peste 100 de caractere."""
    k = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return k.startswith("sk-ant-") and len(k) >= 40


def activ():
    return os.environ.get("MIP_PERMITE_INTREBARI", "").strip() == "1" and cheie_reala()


def model():
    return os.environ.get("MIP_INTREABA_MODEL", "").strip() or MODEL_IMPLICIT


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
        "Ești interpretul paginii „Întreabă datele” din Marketing Command Center (Libra Bank).",
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
        "- categorie: doar la dobânzi (depozite, credite, conturi și carduri); la comisioane, null.",
        "- termen și produs_credit: doar dacă întrebarea le spune.",
        "- Dacă primești interpretarea întrebării anterioare, întrebarea curentă o poate continua "
        "(„și la BRD?”, „dar pe 6 luni?”): păstrezi ce nu se schimbă.",
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
        "Categorii: " + "; ".join(f"{k} ({v})" for k, v in ctx["categorii"].items()),
        "Termene: " + "; ".join(f"{k} ({v})" for k, v in ctx["termene"].items()),
        "Tipuri de credit: " + "; ".join(f"{k} ({v})" for k, v in ctx["produse"].items()),
    ]
    return "\n".join(linii)


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
    curat["clarificare"] = _text(brut.get("clarificare"), 300)
    if curat["tip"] == "cautare" and not (curat["banci"] and (curat["concept"] or curat["text_cautat"])):
        curat["tip"] = "neclar"
    return curat, banci[MAX_BANCI:]


def _categorie(r):
    return (r.get("cod_scenariu") or "").split("|")[0]


def rezuma(randuri):
    """Pe unitate și categorie: câte valori, intervalul, câte gratuite; fără cele ambigue, ca în Sertar.

    Pe categorie, nu doar pe unitate: `nominala` e și dobânda de depozit, și cea de credit, iar fără
    categorie în întrebare un singur interval le-ar amesteca (6,5% la depozit cu 9,9% la ipotecar).
    """
    grupe = {}
    for r in randuri:
        v = r.get("valoare")
        if r.get("ambiguu") or v is None:
            continue
        cheie = (r.get("unitate") or "", _categorie(r))
        g = grupe.setdefault(cheie, {"unitate": cheie[0], "categorie": cheie[1], "n": 0,
                                     "minim": v, "maxim": v, "gratuite": 0})
        g["n"] += 1
        g["minim"] = min(g["minim"], v)
        g["maxim"] = max(g["maxim"], v)
        g["gratuite"] += int(v == 0)
    return sorted(grupe.values(), key=lambda g: (-g["n"], g["categorie"], g["unitate"]))


class Intrebari:
    """O întrebare → interpretarea modelului → valorile din bază. Fără HTTP și fără SQL: serverul
    dă funcțiile de citire (`context`, `cauta`, `stare_banca`), ca la `rulari.Rulari`."""

    def __init__(self, context, cauta, stare_banca, client=None, dir_jurnal=DIR_JURNAL):
        self._sursa_context = context
        self._cauta = cauta
        self._stare_banca = stare_banca
        self._client = client
        self.dir = dir_jurnal
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
            self._client = anthropic.Anthropic(timeout=TIMEOUT_S, max_retries=2)
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
        randuri = self._cauta(banca, interp["concept"], interp["categorie"], interp["termen"],
                              interp["produs_credit"], text)
        return {
            "banca": banca,
            "mod": "text" if text else "concept",
            "total": len(randuri),
            # căutarea după text e tăiată la MAX_RANDURI în SQL, deci totalul real poate fi mai mare
            "limitat": bool(text) and len(randuri) >= MAX_RANDURI,
            "ambigue": sum(1 for r in randuri if r.get("ambiguu")),
            "rezumat": rezuma(randuri),
            "randuri": randuri[:MAX_RANDURI],
            "stare_banca": None if randuri else self._stare_banca(banca),
        }

    def intreaba(self, intrebare, anterior=None):
        intrebare = verifica_intrebarea(intrebare)
        anterior = verifica_anterior(anterior)
        ctx, sistem, sch = self._context()
        m = model()
        rand = {"data": _acum(), "intrebare": intrebare, "model": m}
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
        raspunsuri = [self._raspuns(b, interp) for b in interp["banci"]] if interp["tip"] == "cautare" else []
        cost = preturi.cost(m, tokeni["intrare"], tokeni["iesire"], tokeni["citire_cache"], tokeni["scriere_cache"])
        rand.update(interpretare=interp, stop=stop, randuri={r["banca"]: r["total"] for r in raspunsuri},
                    tokeni=tokeni, cost_usd=cost)
        self._jurnal(rand)
        return {"interpretare": interp, "ignorate": ignorate, "raspunsuri": raspunsuri,
                "model": m, "tokeni": tokeni, "cost_usd": cost}

    def _jurnal(self, rand):
        """Un rând pe întrebare, ca să se vadă unde greșește interpretarea. Nu oprește răspunsul."""
        try:
            os.makedirs(self.dir, exist_ok=True)
            with self._lacat_jurnal:
                with open(os.path.join(self.dir, rand["data"][:7] + ".jsonl"), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rand, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass
