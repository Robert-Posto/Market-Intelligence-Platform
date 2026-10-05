"""Încarcă datele Android ale băncilor (pachetul lui Nicolae) în tabelele android_* (migrarea 027).

De unde: pachetul „MIP_android_pentru_Robert_<data>”, folderul cu `CITESTE_INTAI.md`,
`MANIFEST.csv` și `date/*.csv`. Analiză statică a APK-urilor (manifest, resurse, lista
fișierelor) și pornirea aplicațiilor pe un telefon de test; fără Play Store, fără
decompilare, fără date de utilizator. Se încarcă doar tabelele cu informații despre
aplicații; `ecrane.csv` (capturi, reconstrucții) și imaginile rămân în pachet.

Înainte de orice scriere: fiecare CSV din `date/` trebuie să aibă exact sha256-ul din
`MANIFEST.csv` (altfel nu se scrie nimic).

Idempotent: rândurile poartă `provenienta` (implicit `android_static_<data din numele
pachetului>`); o reîncărcare șterge și rescrie doar rândurile aceleiași proveniențe,
totul într-o singură tranzacție.

Rulare:
    python ingest/load_android.py <folderul pachetului>
    python ingest/load_android.py <folderul pachetului> --uscat     # doar verifică și numără
"""

import argparse
import csv
import hashlib
import os
import re
import sys

import psycopg2
import psycopg2.extras

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import config                      # noqa: E402
import normalizeaza as N           # noqa: E402

# fișier CSV -> (tabelă, coloane în ordinea din CSV, coloane întregi)
TABELE = {
    "versiuni.csv": ("android_versiuni",
                     ["package", "version_name", "version_code", "min_sdk", "target_sdk", "framework",
                      "nr_permisiuni", "nr_trackere", "nr_biblioteci", "nr_librarii_native",
                      "nr_fisiere_apk", "sha256_base_apk", "data_extragere"],
                     {"version_code", "min_sdk", "target_sdk", "nr_permisiuni", "nr_trackere",
                      "nr_biblioteci", "nr_librarii_native", "nr_fisiere_apk"}),
    "permisiuni.csv": ("android_permisiuni", ["package", "version_name", "permisiune"], set()),
    "trackere.csv": ("android_trackere", ["package", "version_name", "tracker", "categorii", "dovada"], set()),
    "biblioteci.csv": ("android_biblioteci", ["package", "version_name", "biblioteca", "versiune"], set()),
    "functionalitati.csv": ("android_functionalitati",
                            ["package", "functie", "titlu", "verdict", "surse", "dovada_text"], set()),
    "portofele.csv": ("android_portofele",
                      ["package", "ropay_text", "googlepay_text", "applepay_text_ios", "wearable_text",
                       "hce_servicii", "nfc_permisiune", "gpay_push_provisioning", "gpay_wallet_api",
                       "cauta_google_wallet"],
                      {"ropay_text", "googlepay_text", "applepay_text_ios", "wearable_text", "hce_servicii",
                       "nfc_permisiune", "gpay_push_provisioning", "gpay_wallet_api", "cauta_google_wallet"}),
    "profil_tehnic.csv": ("android_profil_tehnic", ["package", "tip", "valoare"], set()),
    "schimbari_versiuni.csv": ("android_schimbari_versiuni",
                               ["package", "de_la", "la", "camp", "adaugat", "eliminat"], set()),
    "texte_ecran.csv": ("android_texte_ecran", ["package", "sursa", "data", "pas", "text"], {"pas"}),
    "note.csv": ("android_note", ["package", "nota"], set()),
}
APLICATII = ["slug_banca", "aplicatie", "package", "rol", "versiune_analizata", "versiune_cea_mai_noua",
             "version_code_cea_mai_noua", "framework", "platforma_tehnica", "captura", "min_sdk",
             "target_sdk", "nr_permisiuni", "nr_texte_in_apk"]
APLICATII_INT = {"version_code_cea_mai_noua", "min_sdk", "target_sdk", "nr_permisiuni", "nr_texte_in_apk"}


def citeste(cale):
    with open(cale, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def valoare(col, v, intregi):
    """Textul rămâne exact cum e în CSV (un spațiu sau un NBSP citit de pe ecran e o valoare
    reală, nu lipsă); doar celula complet goală devine NULL."""
    if col in intregi:
        v = (v or "").strip()
        return int(v) if v else None
    return None if v is None or v == "" else v


def verifica_manifest(folder):
    """Toate CSV-urile din date/ au sha256-ul din MANIFEST.csv; altfel oprire."""
    manifest = {r["fisier"].replace("\\", "/"): r["sha256"].lower()
                for r in citeste(os.path.join(folder, "MANIFEST.csv"))}
    for f in ["aplicatii.csv", *TABELE]:
        rel = f"date/{f}"
        if rel not in manifest:
            sys.exit(f"{rel} lipsește din MANIFEST.csv: pachetul nu e complet")
        with open(os.path.join(folder, "date", f), "rb") as fh:
            h = hashlib.sha256(fh.read()).hexdigest()
        if h != manifest[rel]:
            sys.exit(f"{rel}: sha256 diferit de MANIFEST.csv (fișier modificat sau incomplet); nu scriu nimic")


def provenienta_implicita(folder):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(os.path.normpath(folder)))
    return f"android_static_{m.group(1)}" if m else "android_static"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", help="folderul pachetului (cel cu MANIFEST.csv și date/)")
    ap.add_argument("--provenienta", help="eticheta rândurilor (implicit din data pachetului)")
    ap.add_argument("--uscat", action="store_true", help="doar verifică și numără, fără scriere")
    a = ap.parse_args()
    config.incarca()
    folder = os.path.abspath(a.folder)
    if not os.path.isfile(os.path.join(folder, "MANIFEST.csv")):
        # acceptă și folderul exterior al arhivei dezarhivate (pachetul e un nivel mai jos)
        interior = [d for d in os.listdir(folder) if os.path.isfile(os.path.join(folder, d, "MANIFEST.csv"))]
        if len(interior) != 1:
            sys.exit(f"Nu găsesc MANIFEST.csv în {folder}")
        folder = os.path.join(folder, interior[0])
    verifica_manifest(folder)
    prov = a.provenienta or provenienta_implicita(folder)
    date = {f: citeste(os.path.join(folder, "date", f)) for f in ["aplicatii.csv", *TABELE]}
    print(f"pachet: {folder}\nproveniență: {prov}  (sha256 verificat pe {len(date)} fișiere)")
    for f, rows in date.items():
        print(f"  {f:24} {len(rows):5} rânduri")
    if a.uscat:
        return 0

    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT slug, id FROM banci")
            banci = dict(cur.fetchall())
            lipsa = sorted({r["slug_banca"] for r in date["aplicatii.csv"]} - set(banci))
            if lipsa:
                sys.exit(f"Bănci necunoscute în aplicatii.csv: {', '.join(lipsa)}; nu scriu nimic")
            for tabela, _, _ in TABELE.values():
                cur.execute(f"DELETE FROM {tabela} WHERE provenienta = %s", (prov,))
            cur.execute("DELETE FROM android_aplicatii WHERE provenienta = %s", (prov,))

            randuri = []
            for r in date["aplicatii.csv"]:
                vals = [valoare(c, r.get(c), APLICATII_INT) for c in APLICATII[1:]]
                randuri.append((banci[r["slug_banca"]], *vals, prov))
            psycopg2.extras.execute_values(cur, f"""
                INSERT INTO android_aplicatii (id_banca, {', '.join(APLICATII[1:])}, provenienta)
                VALUES %s
                ON CONFLICT (package) DO UPDATE SET
                  {', '.join(f'{c} = EXCLUDED.{c}' for c in APLICATII[1:] if c != 'package')},
                  id_banca = EXCLUDED.id_banca, provenienta = EXCLUDED.provenienta, incarcat_la = now()""",
                randuri)

            scrise = {"aplicatii.csv": len(randuri)}
            for f, (tabela, coloane, intregi) in TABELE.items():
                rows = [tuple(valoare(c, r.get(c), intregi) for c in coloane) + (prov,) for r in date[f]]
                if rows:
                    psycopg2.extras.execute_values(
                        cur, f"INSERT INTO {tabela} ({', '.join(coloane)}, provenienta) VALUES %s", rows,
                        page_size=1000)
                cur.execute(f"SELECT count(*) FROM {tabela} WHERE provenienta = %s", (prov,))
                scrise[f] = cur.fetchone()[0]
            gresite = {f: (len(date[f]), n) for f, n in scrise.items() if n != len(date[f])}
            if gresite:
                raise SystemExit(f"Numărătoare diferită (CSV, bază): {gresite}; tranzacția se anulează")
    print("încărcat:", ", ".join(f"{f.removesuffix('.csv')} {n}" for f, n in scrise.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
