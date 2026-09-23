"""Găsește id-ul de App Store al fiecărei bănci, prin iTunes Search API.

De ce: secțiunile 2.3 (aplicații mobile) și 2.7 (sentiment) stăteau la TREI
bănci din treizeci. Nu era o limită tehnică — id-urile de aplicație se
adăugau de mână, câte unul, și nimeni nu adăugase decât trei. Un singur
script le găsește pentru toate, iar ambele secțiuni se umplu dintr-o rulare.

Cum: `itunes.apple.com/search` cu numele băncii, în storefront-ul românesc,
limitat la software. Gratuit, fără cheie, aceeași familie de API ca Lookup-ul
pe care îl folosim deja.

Problema reală nu e găsirea, ci CONFIRMAREA. O căutare după „ING" întoarce
zeci de aplicații din toată lumea, iar o aplicație greșită atribuită unei
bănci strică ambele secțiuni fără să se vadă. De aceea fiecare candidat trece
prin trei verificări, toate obiective:

  1. `sellerName` sau `bundleId` trebuie să conțină un semn al băncii
     (domeniul ei, fără TLD). Editorul aplicației e cel mai tare semnal:
     „ING Bank N.V." publică aplicația ING, nimeni altcineva nu poate.
  2. aplicația trebuie să fie listată în storefront-ul `ro`
  3. categoria trebuie să fie Finance (6015) sau Business (6000)

Ce nu trece toate trei nu se scrie — se raportează ca necesitând confirmare
umană. Mai bine trei bănci corecte decât treizeci din care cinci mint.

Scrie un JSON, nu în bază: încărcarea rămâne treaba lui `load_appstore.py`,
care aduce și versiunile, și review-urile.

Rulare:  python ingest/cauta_app_id.py
         python ingest/cauta_app_id.py --banca ing
"""

import argparse
import collections
import io
import json
import os
import re
import sys
import time
import urllib.parse

import psycopg2
import requests

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AICI))
sys.path.insert(0, AICI)
import config                      # noqa: E402
import normalizeaza as N           # noqa: E402

IESIRE = os.path.join(os.path.dirname(AICI), "date", "app_id_gasite.json")

# iTunes Search acceptă ~20 cereri/minut per IP, ca și Lookup-ul.
PAUZA = 3.5
CATEGORII_OK = {6015, 6000}        # Finance, Business
UA = {"User-Agent": "MIP/1.0 (monitorizare concurenta; contact IT Libra Bank)"}


def semne(slug, nume, domenii):
    """Cuvintele care trebuie să apară la editor sau în bundleId.

    Domeniul băncii e cel mai bun semn: `bancatransilvania` din
    `bancatransilvania.ro` apare în `ro.btrl.pay`? Nu — de aceea se adaugă și
    slug-ul și cuvintele din nume, iar potrivirea cere UNUL dintre ele.
    """
    s = {slug.replace("-", "")}
    for d in domenii:
        gazda = urllib.parse.urlparse(d).netloc.lower()
        gazda = re.sub(r"^www\.", "", gazda)
        radacina = gazda.split(".")[0]
        if len(radacina) >= 4:
            s.add(radacina)
    for cuvant in re.findall(r"[a-zăâîșț]{4,}", (nume or "").lower()):
        if cuvant not in ("bank", "banca", "banka", "sucursala", "romania",
                          "internet", "grupe", "societe", "generale"):
            s.add(cuvant)
    return {x for x in s if len(x) >= 4}


def cauta(termen, err):
    u = ("https://itunes.apple.com/search?" + urllib.parse.urlencode({
        "term": termen, "country": "ro", "entity": "software", "limit": 25}))
    try:
        r = requests.get(u, headers=UA, timeout=25)
    except requests.exceptions.RequestException as exc:
        err.write(f"    cerere eșuată: {type(exc).__name__}\n")
        return []
    if not r.ok:
        err.write(f"    HTTP {r.status_code}\n")
        return []
    try:
        return r.json().get("results", [])
    except ValueError:
        return []


# A patra verificare: aplicația e pentru piața DIN ROMÂNIA?
#
# Grupul corect nu e destul, și asta s-a văzut pe date, nu în teorie:
#   banorient  -> BANOtouch, „Banque Banorient France"  = aplicația mamei
#   bnpparibas -> „Mes Comptes BNP Paribas"             = aplicația franceză
#   pko        -> IKO, „PKO Bank Polski"                = aplicația poloneză
#   citibank   -> CitiManager Corporate Cards           = unealtă globală
# Recenziile lor vin de la clienți francezi sau polonezi. Pentru monitorizarea
# concurenței DIN ROMÂNIA, nota și textele lor nu spun nimic despre sucursala
# de aici — sunt zgomot care arată ca date.
#
# Aceeași verificare prinde și un fals pozitiv de grup: `tbi` potrivea
# „TBI Banking" publicat de Trade Bank of Iraq, fiindcă «tbibank» apare în
# `com.tbi.tbibanking`. Altă bancă, alt continent. Fără semn de România, nu
# se acceptă automat.
RE_PIATA_RO = re.compile(r"(^|[^a-z])ro([^a-z]|$)|roman|rom[âa]nia", re.I)


def e_pentru_romania(a):
    """Semn obiectiv că aplicația servește piața din România.

    Două căi, amândouă din date, nu din presupuneri:

    1. marcaj explicit de țară în `bundleId`, titlu sau editor
       (`ro.raiffeisen.new.smartmobile`, „Garanti BBVA Romania")

    2. aplicația declară că suportă limba română. Verificat pe cazurile
       respinse de prima cale: Credex declară RO ca singură limbă, Revolut o
       are între 24 — amândouă servesc clienți români. În schimb TBI Banking
       (Trade Bank of Iraq) declară AR+EN, IKO declară EN/PL/RU/UK, iar
       „Mes Comptes BNP Paribas" doar FR. Semnalul separă exact cazurile pe
       care prima cale le rata.

    Limită cunoscută și neacoperită: TechVentures ONline e publicat de
    `Techventures Bank SA`, o bancă românească, dar declară doar EN. Ar fi
    prins de o a treia regulă „numele editorului seamănă cu numele băncii" —
    dar aceeași regulă ar accepta greșit BANOtouch, al cărui editor
    („Banque Banorient France") seamănă la fel de bine cu numele sucursalei
    din România. O regulă care repară un caz și strică altul deja văzut nu se
    adaugă; TechVentures rămâne pentru confirmare umană.
    """
    for camp in ("bundleId", "trackName", "sellerName"):
        v = a.get(camp) or ""
        if RE_PIATA_RO.search(v):
            return True, f"«{v[:38]}»"
    limbi = [str(x).upper() for x in (a.get("languageCodesISO2A") or [])]
    if "RO" in limbi:
        return True, f"limba română declarată (din {len(limbi)} limbi)"
    return False, None


def potriveste(rezultate, cuvinte):
    """Primul rezultat care trece toate verificările, cu motivul.

    Întoarce (aplicație, motiv, sigur_pentru_romania). Un rezultat care trece
    verificările de grup dar nu pe cea de piață NU se aruncă: se întoarce cu
    steagul pe fals, ca să ajungă în lista de confirmat de om, nu în bază.
    """
    rezerva = None
    for a in rezultate:
        editor = (a.get("sellerName") or "").lower()
        bundle = (a.get("bundleId") or "").lower()
        titlu = (a.get("trackName") or "").lower()
        gasit = next((c for c in cuvinte
                      if c in editor or c in bundle or c in titlu), None)
        if not gasit:
            continue
        genuri = set(int(g) for g in (a.get("genreIds") or []) if str(g).isdigit())
        if not (genuri & CATEGORII_OK):
            continue
        unde = ("editor" if gasit in editor else
                "bundleId" if gasit in bundle else "titlu")
        baza = f"«{gasit}» în {unde}; categorie {sorted(genuri & CATEGORII_OK)}"
        ro, unde_ro = e_pentru_romania(a)
        if ro:
            return a, f"{baza}; piață RO confirmată în {unde_ro}", True
        if rezerva is None:
            rezerva = (a, f"{baza}; DAR fără semn că e aplicația din România", False)
    return rezerva if rezerva else (None, None, False)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--banca", help="doar o bancă (slug)")
    a = ap.parse_args()

    config.incarca()
    err = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", write_through=True)
    raport = collections.Counter()

    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT b.slug, b.nume,
                          coalesce(array_agg(DISTINCT s.sursa)
                                   FILTER (WHERE s.tip_sursa = 'url'), '{}') AS domenii,
                          (SELECT app_id FROM app_release ar
                            WHERE ar.id_banca = b.id AND ar.platforma = 'ios'
                            LIMIT 1) AS are_deja
                   FROM banci b LEFT JOIN surse s ON s.id_banca = b.id
                   WHERE (%s = '' OR b.slug = %s)
                   GROUP BY b.id, b.slug, b.nume ORDER BY b.slug""",
                (a.banca or "", a.banca or ""),
            )
            banci = cur.fetchall()

    gasite, incerte = {}, []
    for slug, nume, domenii, are_deja in banci:
        if are_deja:
            gasite[slug] = {"ios_app_id": int(are_deja), "sursa_id": "deja în bază"}
            raport["deja_in_baza"] += 1
            continue
        cuvinte = semne(slug, nume, domenii)
        err.write(f"{slug:20s} caut «{nume[:42]}»\n")
        ales, motiv, sigur = None, None, False
        # Se încearcă numele complet, apoi slug-ul: unele bănci publică sub un
        # nume de produs („George", „BT Pay"), nu sub numele lor legal.
        for termen in (nume, slug.replace("-", " ")):
            rez = cauta(termen, err)
            time.sleep(PAUZA)
            ales, motiv, sigur = potriveste(rez, cuvinte)
            if sigur:
                break            # piață RO confirmată: nu mai căutăm
        if not ales:
            err.write(f"{'':20s} -- niciun rezultat confirmat\n")
            incerte.append((slug, nume, "niciun rezultat care să treacă verificările"))
            raport["neconfirmate"] += 1
            continue
        if not sigur:
            # Grup corect, piață neconfirmată. NU se scrie: recenziile unei
            # aplicații franceze sau poloneze nu spun nimic despre sucursala
            # din România, dar arată exact ca niște date bune.
            err.write(f"{'':20s} ?? {ales['trackId']} · "
                      f"{str(ales.get('trackName'))[:30]:32s} · {motiv}\n")
            incerte.append((slug, nume,
                            f"{ales.get('trackName')} ({ales.get('sellerName')})"))
            raport["piata_neconfirmata"] += 1
            continue
        gasite[slug] = {
            "ios_app_id": ales["trackId"],
            "nume_app": ales.get("trackName"),
            "editor": ales.get("sellerName"),
            "bundle": ales.get("bundleId"),
            "confirmare": motiv,
        }
        err.write(f"{'':20s} OK {ales['trackId']} · {str(ales.get('trackName'))[:34]:36s} "
                  f"· {motiv}\n")
        raport["gasite"] += 1

    os.makedirs(os.path.dirname(IESIRE), exist_ok=True)
    with io.open(IESIRE, "w", encoding="utf-8") as f:
        json.dump(gasite, f, ensure_ascii=False, indent=1, sort_keys=True)

    if incerte:
        err.write("\n--- NU se scriu, cer confirmare umană ---\n")
        for slug, nume, motiv in incerte:
            err.write(f"  {slug:18s} {nume[:32]:34s} {motiv[:72]}\n")
        err.write("O aplicație a grupului, dar de pe altă piață, e mai rea decât\n"
                  "lipsa unei aplicații: arată ca date bune și nu e.\n")
    err.write(f"\nScris în {IESIRE}\n")
    N.raporteaza(raport, sys.stderr)


if __name__ == "__main__":
    main()
