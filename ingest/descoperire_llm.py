"""Banda A2: descoperire prin LLM (Anthropic), doar pentru ce n-au găsit scraperele.

Adaptat din `flux-colectare/claudeCrawl.py` (colegul). Modelul folosește
`web_search` și `web_fetch` din infrastructura Anthropic (agent `Claude-User`,
robots.txt respectat de ei), limitate la domeniile băncii.

Față de original:
  - caută DOAR produsele fără nicio sursă activă după A1 (`goluri`), nu tot
    site-ul: A1 a găsit deja 5.023 de adrese;
  - NU rulează pe băncile care ne-au blocat (sursa principală `blocat`):
    regula echipei — o bancă blocată nu se accesează prin alt canal;
  - fiecare adresă propusă e verificată de scraperul nostru (robots.txt, UA
    echipei, răspuns OK) și clasificată ca orice altă sursă, înainte de scriere;
  - costul (tokeni) se înregistrează: originalul nu-l înregistra deloc;
  - produsele vin din tabela `produse`, nu dintr-o listă proprie de 13.

Descoperirea scrie DOAR în `surse` (figura 2). Nicio cifră de aici nu ajunge
în `observations`: sursele noi se extrag apoi cu `populare_initiala --banca`.

Rulare:
    python ingest/descoperire_llm.py --banca vista            # doar propune + cost
    python ingest/descoperire_llm.py --banca vista --scrie    # și scrie în surse
    python ingest/descoperire_llm.py --toate --scrie
"""

import argparse
import collections
import json
import os
import sys
from urllib.parse import urlparse

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import config                      # noqa: E402
import descoperire                 # noqa: E402
import normalizeaza as N           # noqa: E402
import transport                   # noqa: E402
from banks import BANKS            # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = os.environ.get("MODEL", "claude-sonnet-5")
MAX_PAGINI = int(os.environ.get("MAX_PAGINI", "15"))
MAX_CAUTARI = int(os.environ.get("MAX_CAUTARI", "5"))
TURE_MAX = int(os.environ.get("TURE_MAX", "8"))


class Cost:
    def __init__(self):
        self.intrare = self.iesire = 0

    def adauga(self, usage):
        self.intrare += usage.input_tokens
        self.iesire += usage.output_tokens


def domenii(url_banca):
    gazda = urlparse(url_banca).netloc.lower().removeprefix("www.")
    return [gazda, f"www.{gazda}"]


def banci_blocate(cur):
    cur.execute("""SELECT DISTINCT b.slug FROM surse s JOIN banci b ON b.id = s.id_banca
                   WHERE s.status = 'blocat' AND s.rol = 'hub'""")
    return {r[0] for r in cur.fetchall()}


def goluri(cur, slug):
    """Produsele pentru care banca nu are nicio sursă activă."""
    cur.execute("""SELECT p.nume FROM produse p
                   WHERE NOT EXISTS (
                     SELECT 1 FROM surse_produse sp JOIN surse s ON s.id = sp.id_sursa
                     JOIN banci b ON b.id = s.id_banca
                     WHERE sp.id_produs = p.id AND b.slug = %s AND s.status = 'activ')
                   ORDER BY p.nume""", (slug,))
    return [r[0] for r in cur.fetchall()]


def _unelte(dom, produse):
    gata = {
        "name": "gata",
        "description": "Returnează adresele găsite. Se apelează o singură dată, la sfârșit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "documente": {"type": "array", "items": {"type": "object", "properties": {
                    "url": {"type": "string",
                            "description": "Adresa exactă pe care ai deschis-o. Nu o reconstrui."},
                    "produse": {"type": "array", "items": {"type": "string", "enum": produse}},
                    "dovada": {"type": "string",
                               "description": "Cifra sau titlul văzut, care justifică asocierea."},
                }, "required": ["url", "produse", "dovada"]}},
                "negasite": {"type": "array", "items": {"type": "string", "enum": produse}},
            },
            "required": ["documente", "negasite"],
        },
    }
    return [
        {"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": MAX_PAGINI,
         "allowed_domains": dom, "max_content_tokens": 12000},
        {"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_CAUTARI,
         "allowed_domains": dom},
        gata,
    ]


def _sistem(produse):
    return (
        "Cauți pe site-ul unei bănci din România paginile și documentele publice pentru "
        f"produsele: {', '.join(produse)}. Celelalte produse au fost deja găsite; nu le căuta.\n"
        "Folosește web_search pe domeniul băncii și web_fetch pe rezultate. Documentele de "
        "tarife („Tarife și comisioane”, „Documente utile”, de obicei în footer) acoperă multe "
        "produse deodată.\n"
        "Pui o adresă doar dacă ai VĂZUT în conținut date despre produs (o dobândă, un "
        "comision, un exemplu reprezentativ); la `dovada` scrii exact ce ai văzut. Nu inventa "
        "adrese și nu le reconstrui din memorie. Ce nu găsești trece la `negasite` — e un "
        "rezultat valid. Închei apelând `gata` o singură dată.")


def _curata(content):
    """Scoate apelurile de unelte rămase fără rezultat (API-ul le refuză la retrimitere)."""
    cu = {getattr(b, "tool_use_id", None) for b in content
          if b.type in ("web_fetch_tool_result", "web_search_tool_result")}
    return [b for b in content if not (b.type == "server_tool_use" and b.id not in cu)]


def ruleaza_banca(slug, url_banca, lipsa, client=None):
    if client is None:
        from anthropic import Anthropic
        client = Anthropic()
    cost, deschise = Cost(), []
    mesaje = [{"role": "user", "content": f"Banca: {slug}\nPagina principală: {url_banca}"}]
    for _tura in range(TURE_MAX):
        with client.beta.messages.stream(
                model=MODEL, max_tokens=8000, system=_sistem(lipsa),
                tools=_unelte(domenii(url_banca), lipsa), messages=mesaje,
                betas=["web-fetch-2025-09-10"]) as f:
            r = f.get_final_message()
        cost.adauga(r.usage)
        deschise += [b.input.get("url", "") for b in r.content
                     if b.type == "server_tool_use" and b.name == "web_fetch"]
        final = [b for b in r.content if b.type == "tool_use" and b.name == "gata"]
        if final:
            return {**final[0].input, "cost": cost, "deschise": deschise}
        mesaje.append({"role": "assistant", "content": _curata(r.content)})
        mesaje.append({"role": "user", "content": "Continuă; când ai terminat, apelează `gata`."})
    return {"documente": [], "negasite": lipsa, "cost": cost, "deschise": deschise,
            "eroare": f"{TURE_MAX} ture fără `gata`"}


def verifica_si_scrie(cur, slug, docs, produse_id, scrie, stare, raport):
    for d in docs:
        u = descoperire.normalizeaza_url(d["url"])
        c = descoperire.clasifica_adresa(u, d.get("dovada", ""))
        rez = transport.adu(u, slug, stare)     # scraperul NOSTRU confirmă adresa
        if rez.verdict != "OK" or not c:
            raport[f"llm_respinse_{rez.verdict if rez.verdict != 'OK' else 'neclasificat'}"] += 1
            continue
        raport["llm_confirmate"] += 1
        print(f"      + {u[:90]}  {d.get('produse')}  „{(d.get('dovada') or '')[:60]}”")
        if not scrie:
            continue
        cur.execute(
            """INSERT INTO surse (id_banca, tip_sursa, sursa, rol, format, metoda, status,
                   frecventa, nota_extractie)
               SELECT id, 'url', %s, %s, %s, 'http', 'activ', 'lunar', 'descoperit prin LLM'
               FROM banci WHERE slug = %s ON CONFLICT DO NOTHING RETURNING id""",
            (u, c["rol"], c["format"], slug))
        r = cur.fetchone()
        for p in (d.get("produse") or []):
            if r and p in produse_id:
                cur.execute("INSERT INTO surse_produse (id_sursa, id_produs) VALUES (%s, %s)",
                            (r[0], produse_id[p]))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca")
    ap.add_argument("--toate", action="store_true")
    ap.add_argument("--scrie", action="store_true")
    a = ap.parse_args()
    config.incarca()
    stare, raport = {}, collections.Counter()
    total = Cost()
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nume, id FROM produse")
            produse_id = dict(cur.fetchall())
            cur.execute("SELECT nume, slug FROM banci")
            slug_dupa_nume = dict(cur.fetchall())
            blocate = banci_blocate(cur)
            for b in BANKS:
                slug = slug_dupa_nume.get(b["name"])
                if not slug or (a.banca and slug != a.banca) or not (a.banca or a.toate):
                    continue
                if slug in blocate:
                    print(f"  {slug:20s} SĂRITĂ — ne-a blocat; fără alt canal")
                    continue
                lipsa = goluri(cur, slug)
                if not lipsa:
                    print(f"  {slug:20s} nimic lipsă")
                    continue
                rez = ruleaza_banca(slug, b["url"], lipsa)
                total.intrare += rez["cost"].intrare
                total.iesire += rez["cost"].iesire
                print(f"  {slug:20s} lipsă {len(lipsa)} · {len(rez.get('documente', []))} propuse · "
                      f"{rez['cost'].intrare} tokeni intrare, {rez['cost'].iesire} ieșire"
                      + (f" · {rez['eroare']}" if rez.get("eroare") else ""))
                verifica_si_scrie(cur, slug, rez.get("documente", []), produse_id, a.scrie,
                                  stare, raport)
                conn.commit()
    transport.inchide(stare)
    print(f"\nTOTAL: {total.intrare} tokeni intrare, {total.iesire} tokeni ieșire")
    for k in sorted(raport):
        print(f"{raport[k]:6d}  {k}")


if __name__ == "__main__":
    main()
