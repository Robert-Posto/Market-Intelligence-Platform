"""Actualizează aplicația mobilă a unei bănci pe ambele platforme, iOS și Android, și îi reface brief-ul AI.

Doi pași, pentru o singură bancă:

1. COLECTAREA, cu colectoarele care există deja și toate regulile lor (robots.txt, origine
   BLOCAT, oprire la 429, MIP_SALT):

     iOS      python ingest/load_mobil.py --banca <slug>
              versiunea, nota, numărul de note, capturile (Lookup, itunes.apple.com) + recenziile
              și stelele (pagina apps.apple.com) -> Postgres: app_release, app_screenshot, app_review
     Android  node ingest/google_play_app.mjs <slug> --salveaza
              versiunea, nota, evaluările, descărcările, capturile și recenziile din pagina Google
              Play -> date/google_play.json + date/google_play_recenzii.json

2. BRIEF-UL AI („Rezumat AI” din 2.3): recenziile disponibile pe fiecare platformă (iOS din
   app_review, Android din google_play_recenzii.json) trec prin `brief_recenzii.genereaza_brief`,
   ambele platforme în paralel, iar rezultatul se scrie în date/rezumate_recenzii.json (iOS) și
   date/rezumate_recenzii_play.json (Android), doar intrarea băncii. Apelul la model costă
   (~$0,04 pe platformă pentru 23 de recenzii ING, 07.10.2026), de aceea:
     - se sare dacă recenziile sunt aceleași ca la brief-ul existent (amprenta lor), afară de --forteaza;
     - toată rularea (colectare + brief) e un job în „Joburi și erori” (tipul aplicatii_mobile,
       migrarea 039), cu durata, tokenii, costul și erorile pe platformă.

Ce NU actualizează: analiza statică a APK-urilor (permisiuni, trackere, biblioteci, tabelele
android_*). Vine din pachetul lui Nicolae, făcut pe un telefon de test, și se încarcă cu
`load_android.py <folder>`; nu se poate reface prin rețea.

Rulare (din rădăcina repo-ului):
    python ingest/actualizeaza_aplicatii.py ing
    python ingest/actualizeaza_aplicatii.py ing --doar ios
    python ingest/actualizeaza_aplicatii.py ing --fara-brief    # doar colectarea, fără model
    python ingest/actualizeaza_aplicatii.py ing --forteaza      # brief nou chiar dacă recenziile sunt aceleași
    python ingest/actualizeaza_aplicatii.py ing --simulare      # ce s-ar face, fără cereri și fără scriere
    python ingest/actualizeaza_aplicatii.py --banca ing         # forma din „Rulare manuală” (app/rulari.py)

Cod de ieșire: 0 dacă fiecare platformă cu aplicație s-a actualizat și brief-ul s-a făcut (sau
nu era nevoie de el), 1 altfel.
"""

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import date

import psycopg2

AICI = os.path.dirname(os.path.abspath(__file__))
RADACINA = os.path.dirname(AICI)
sys.path[:0] = [RADACINA, AICI, os.path.join(RADACINA, "extragere_produse_bancare")]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config                      # noqa: E402
import flux                        # noqa: E402
import normalizeaza as N           # noqa: E402

DATE = os.path.join(RADACINA, "date")
FISIER_IOS = os.path.join(DATE, "app_id_gasite.json")
FISIER_PLAY = os.path.join(DATE, "google_play.json")
FISIER_RECENZII_PLAY = os.path.join(DATE, "google_play_recenzii.json")
# Lookup-ul (versiuni, note, capturi) și pagina aplicației (recenzii, stele) sunt origini
# diferite: pe 06.10.2026 apps.apple.com a dat 429 și e BLOCAT, itunes.apple.com nu
ORIGINI_IOS = {"lookup": "https://itunes.apple.com/", "pagina": "https://apps.apple.com/"}
ORIGINE_PLAY = "https://play.google.com/"

# platforma -> (eticheta, fișierul de rezumate citit de 2.3)
PLATFORME = {
    "ios": ("iOS · App Store", os.path.join(DATE, "rezumate_recenzii.json")),
    "android": ("Android · Google Play", os.path.join(DATE, "rezumate_recenzii_play.json")),
}


# ── ce aplicație are banca ────────────────────────────────────────

def aplicatie_ios(slug):
    """Aplicația iOS confirmată de cauta_app_id.py, sau None."""
    try:
        with open(FISIER_IOS, encoding="utf-8") as f:
            return json.load(f).get(slug)
    except FileNotFoundError:
        return None


def aplicatie_android(cur, slug):
    """Pachetul principal din analiza APK (android_aplicatii), altfel din ultima colectare Play.

    Aceeași regulă ca `harta()` din google_play_app.mjs: aplicația principală, iar la Libra
    și cea cu rolul `reper`; o aplicație `secundar` (ex. a doua aplicație a băncii) nu.
    """
    cur.execute("""SELECT a.package, a.aplicatie FROM android_aplicatii a JOIN banci b ON b.id = a.id_banca
                    WHERE b.slug = %s AND a.rol <> 'secundar' ORDER BY a.rol LIMIT 1""", (slug,))
    r = cur.fetchone()
    if r:
        return {"package": r[0], "nume": r[1]}
    x = _json(FISIER_PLAY).get("aplicatii", {}).get(slug)
    return {"package": x["package"], "nume": x.get("nume")} if x else None


# ── recenziile pentru brief ───────────────────────────────────────

def recenzii_ios(slug):
    """Toate recenziile iOS ale băncii din bază: se acumulează, nu se șterg (load_mobil.py)."""
    with psycopg2.connect(N.dsn()) as conn, conn.cursor() as cur:
        cur.execute("""SELECT r.rating, r.text, r.postat_la, r.versiune FROM app_review r
                         JOIN banci b ON b.id = r.id_banca
                        WHERE b.slug = %s AND r.platforma = 'ios'""", (slug,))
        return [{"nota": n, "text": t, "data": d.date().isoformat() if d else None, "versiune": v}
                for n, t, d, v in cur.fetchall()]


def recenzii_android(slug):
    """Recenziile Google Play ale băncii, acumulate de google_play_app.mjs (cele 20 afișate, la fiecare rulare)."""
    rec = _json(FISIER_RECENZII_PLAY).get("aplicatii", {}).get(slug, {}).get("recenzii") or []
    return [{"nota": r.get("nota"), "text": r.get("text"), "data": r.get("data"), "versiune": r.get("versiune")}
            for r in rec]


def amprenta(recenzii):
    """Aceleași recenzii -> aceeași amprentă, indiferent de ordine: brief-ul nu se mai plătește o dată."""
    chei = sorted(json.dumps([r.get("nota"), r.get("data"), r.get("text")], ensure_ascii=False) for r in recenzii)
    return hashlib.sha256("\n".join(chei).encode("utf-8")).hexdigest()[:16]


# ── fișiere ───────────────────────────────────────────────────────

def _json(cale):
    try:
        with open(cale, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def scrie_brief(cale, slug, intrare):
    """Rescrie doar intrarea băncii; celelalte bănci rămân cum erau."""
    d = _json(cale) or {"generat_la": None, "generat_de": None, "aplicatii": {}}
    d.setdefault("aplicatii", {})[slug] = intrare
    # antetul fișierului e citit de tooltip ca „ultimul generat”; fiecare intrare își are datele ei
    d["generat_la"] = intrare["generat_la"]
    d["generat_de"] = intrare["generat_de"]
    temp = f"{cale}.{os.getpid()}.tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(temp, cale)


def ruleaza(comanda, simulare):
    print(f"  $ {' '.join(comanda)}", flush=True)
    if simulare:
        return 0
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    # ieșirea colectoarelor trece direct în consolă: progresul lor e mesajul util
    return subprocess.run(comanda, cwd=RADACINA, env=env).returncode


# ── pasul 1: colectarea ───────────────────────────────────────────

def colecteaza_ios(slug, ios, simulare):
    print(PLATFORME["ios"][0])
    if not ios:
        print("  sărit: banca nu are aplicație iOS confirmată în date/app_id_gasite.json\n"
              "  (python ingest/cauta_app_id.py, apoi confirmarea manuală)\n")
        return "fără aplicație"
    if flux.blocat(ORIGINI_IOS["lookup"]):
        print(f"  sărit: {ORIGINI_IOS['lookup']} e BLOCAT ({flux.blocat(ORIGINI_IOS['lookup'])}); "
              "fără Lookup, load_mobil.py nu scrie nimic\n")
        return "blocat"
    # bcr, ing și libra au doar id-ul: erau „deja în bază” când a rulat cauta_app_id.py
    print(f"  {ios['nume_app'] + ' · ' if ios.get('nume_app') else ''}id {ios['ios_app_id']}")
    motiv = flux.blocat(ORIGINI_IOS["pagina"])
    if motiv:
        print(f"  atenție: {ORIGINI_IOS['pagina']} e BLOCAT ({motiv}): se actualizează versiunea, nota și "
              "capturile, dar nu recenziile și distribuția pe stele")
    cod = ruleaza([sys.executable, os.path.join("ingest", "load_mobil.py"), "--banca", slug], simulare)
    print()
    return "ok" if cod == 0 else f"eșuat (cod {cod})"


def colecteaza_android(slug, android, simulare):
    print(PLATFORME["android"][0])
    node = shutil.which("node")
    motiv = flux.blocat(ORIGINE_PLAY)
    if not android:
        print("  sărit: banca nu are aplicație Android cunoscută (nici în android_aplicatii, "
              "nici în date/google_play.json)\n")
        return "fără aplicație"
    if motiv:
        print(f"  sărit: {ORIGINE_PLAY} e BLOCAT ({motiv}); doar un om îl deblochează\n")
        return "blocat"
    if not node:
        print("  sărit: nu găsesc `node` în PATH (colectorul Play e în Node, cu google-play-scraper)\n")
        return "fără node"
    print(f"  {android['nume'] + ' · ' if android.get('nume') else ''}{android['package']}")
    cod = ruleaza([node, os.path.join("ingest", "google_play_app.mjs"), slug, "--salveaza"], simulare)
    print()
    return "ok" if cod == 0 else f"eșuat (cod {cod})"


# ── pasul 2: brief-ul AI ──────────────────────────────────────────

async def fa_brieful(slug, de_facut, simulare, job):
    """de_facut: {platforma: (nume aplicatie, recenzii)}. Ambele platforme pornesc în același timp.
    Întoarce {platforma: starea}."""
    from brief_recenzii import MODEL, _client, genereaza_brief

    stari = {}
    print("Brief AI")
    if simulare:
        for p, (_, rec) in de_facut.items():
            print(f"  {PLATFORME[p][0]}: {len(rec)} recenzii -> {MODEL} (simulare: fără apel)")
            stari[p] = "ok"
        return stari

    ai = _client()
    platforme = list(de_facut)
    rezultate = await asyncio.gather(
        *(genereaza_brief(rec, aplicatie=nume, platforma=PLATFORME[p][0].split(" · ")[1], ai=ai)
          for p, (nume, rec) in de_facut.items()),
        return_exceptions=True)
    for p, r in zip(platforme, rezultate):
        eticheta, fisier = PLATFORME[p]
        if isinstance(r, BaseException):
            # BriefEsuat, sau o eroare a SDK-ului (cheie, rețea, 429): platforma cealaltă merge mai departe
            job.eroare(f"brief: {type(r).__name__}: {r}", context=p)
            print(f"  {eticheta}: eșuat, {type(r).__name__}: {str(r)[:200]}")
            stari[p] = "eșuat"
            continue
        job.consum(r["model"], r.pop("tokeni"))
        model = r.pop("model")
        scrie_brief(fisier, slug, {**r, "generat_la": str(date.today()),
                                   "generat_de": f"{model}, ingest/brief_recenzii.py",
                                   "amprenta": amprenta(de_facut[p][1])})
        print(f"  {eticheta}: din {r['n_recenzii']} recenzii, {len(r['pro'])} pro, {len(r['contra'])} contra "
              f"-> {os.path.relpath(fisier, RADACINA)}")
        stari[p] = "ok"
    print(f"  cost estimat: ${job.cost:.4f} (prețuri de listă, extragere_produse_bancare/preturi.py)")
    return stari


def pregateste_brieful(slug, nume, ios, android, platforme, forteaza):
    """Ce platforme au nevoie de un brief nou; restul, cu motivul pentru care se sar."""
    de_facut, sarite = {}, {}
    surse = {"ios": (ios, lambda: recenzii_ios(slug), (ios or {}).get("nume_app") or nume),
             "android": (android, lambda: recenzii_android(slug), (android or {}).get("nume") or nume)}
    for p in platforme:
        app, citeste, nume_app = surse[p]
        if not app:
            continue
        rec = [r for r in citeste() if str(r.get("text") or "").strip()]
        if not rec:
            sarite[p] = "nicio recenzie colectată"
            continue
        vechi = _json(PLATFORME[p][1]).get("aplicatii", {}).get(slug) or {}
        if not forteaza and vechi.get("amprenta") == amprenta(rec):
            sarite[p] = f"aceleași {len(rec)} recenzii ca la brief-ul din {vechi.get('generat_la')} (--forteaza îl reface)"
            continue
        de_facut[p] = (nume_app, rec)
    return de_facut, sarite


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("banca", nargs="?", help="slug-ul băncii, ca în tabela banci (ex. ing, banca-transilvania)")
    # „Rulare manuală” pune banca ca --banca, ca la toate comenzile din app/rulari.py
    ap.add_argument("--banca", dest="banca_opt", metavar="BANCA", help="la fel, ca opțiune")
    ap.add_argument("--doar", choices=("ios", "android"), help="doar o platformă")
    ap.add_argument("--fara-brief", action="store_true", help="doar colectarea, fără apel la model")
    ap.add_argument("--forteaza", action="store_true", help="brief nou chiar dacă recenziile n-au schimbat")
    ap.add_argument("--simulare", action="store_true", help="arată ce s-ar face, fără cereri și fără scriere")
    a = ap.parse_args()
    a.banca = a.banca or a.banca_opt
    if not a.banca:
        ap.error("lipsește banca (ex. python ingest/actualizeaza_aplicatii.py ing)")

    config.incarca()
    if not os.environ.get("MIP_SALT"):
        # ambele colectoare refuză fără ea; mai bine o dată aici decât de două ori la jumătate
        print("MIP_SALT nu e setat: autorii recenziilor nu se pot pseudonimiza. Opresc.", file=sys.stderr)
        return 1
    try:
        with psycopg2.connect(N.dsn()) as conn, conn.cursor() as cur:
            cur.execute("SELECT nume FROM banci WHERE slug = %s", (a.banca,))
            r = cur.fetchone()
            if not r:
                cur.execute("SELECT slug FROM banci ORDER BY slug")
                print(f"Banca „{a.banca}” nu e în tabela banci. Slug-uri: "
                      f"{', '.join(x[0] for x in cur.fetchall())}", file=sys.stderr)
                return 1
            nume = r[0]
            android = aplicatie_android(cur, a.banca)
    except psycopg2.Error as exc:
        print(f"Baza nu răspunde ({str(exc).strip()[:160]}). Opresc: iOS scrie în bază.", file=sys.stderr)
        return 1
    ios = aplicatie_ios(a.banca)
    platforme = [a.doar] if a.doar else ["ios", "android"]

    from brief_recenzii import MODEL
    from jurnal_joburi import FaraJurnal, Job
    # tot jobul în jurnal (colectare + brief): durata reală pe bancă dă estimarea din „Rulare manuală”
    job = (FaraJurnal() if a.simulare else
           Job("aplicatii_mobile", banca=a.banca, model=None if a.fara_brief else MODEL,
               parametri={"platforme": platforme, "fara_brief": a.fara_brief, "forteaza": a.forteaza}))
    with job:
        print(f"{nume} ({a.banca})\n")
        rezultate = {}
        if "ios" in platforme:
            rezultate["iOS"] = colecteaza_ios(a.banca, ios, a.simulare)
        if "android" in platforme:
            rezultate["Android"] = colecteaza_android(a.banca, android, a.simulare)
        for k, v in rezultate.items():
            if v not in ("ok", "fără aplicație"):
                job.eroare(f"colectarea: {v}", context=k)

        if not a.fara_brief:
            # brief-ul se face și când colectarea unei platforme a eșuat: recenziile deja colectate rămân valabile
            de_facut, sarite = pregateste_brieful(a.banca, nume, ios, android, platforme, a.forteaza)
            if de_facut or sarite:
                stari = asyncio.run(fa_brieful(a.banca, de_facut, a.simulare, job)) if de_facut else {}
                if not de_facut:
                    print("Brief AI")
                for p, motiv in sarite.items():
                    print(f"  {PLATFORME[p][0]}: sărit, {motiv}")
                    rezultate[f"brief {p}"] = "sărit"
                for p, st in stari.items():
                    rezultate[f"brief {p}"] = st
                if any(st == "ok" for st in stari.values()) and not a.simulare:
                    print("  date/rezumate_recenzii*.json se citesc la build: pe :8765/app/ apar după `npm run build`")
                print()

        job.rezumat = " · ".join(f"{k} {v}" for k, v in rezultate.items())
        print("Rezumat: " + job.rezumat)
        if "android" in platforme:
            print("Analiza statică a APK-ului (permisiuni, trackere) nu se reface de aici: load_android.py <pachet>.")
    return 0 if all(v in ("ok", "fără aplicație", "sărit") for v in rezultate.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
