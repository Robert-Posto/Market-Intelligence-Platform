"""Prețurile și dobânzile scrise explicit în catalogul intern Libra -> `observations`.

DE CE: Robert a hotărât ca, pentru Libra, datele luate de pe web să fie
înlocuite cu cele din catalogul intern (`catalog_libra`, migrarea 020), DOAR
acolo unde catalogul le poate înlocui. Catalogul nu are coloane de preț: sumele
și procentele stau în text, în „Caracteristicile produsului"
(„Abonament corporate 225 lei/lună: …", „dobândă ~6,25% p.a."). Modulul de aici
le scoate de acolo și le pune pe conceptele standard (`camp`), ca paginile
Produse (2.1), Rate (2.2) și Versus să lucreze pe ele.

Determinist, fără LLM. Regula de bază: se mapează doar ce e fără echivoc —
o sumă sau un procent SCRIS, legat în text de un serviciu pe care vocabularul
îl are. Tot restul (limite de finanțare, procente de garantare, „gratuit" fără
sumă, două valori fără variantă) iese în raport, cu motivul, și nu se scrie.
Un preț ghicit ar ascunde, prin vedere, valori reale colectate de pe web.

Ce se mapează azi (vezi `extrage`):
  - „Abonament [corporate|operațional] X lei/lună" la un produs de cont
      -> administrare_cont, lei, frecventa 'lunar' (convenția colegului:
         prețul pachetului stă pe administrare_cont)
  - „dobândă … X% [p.a.] [la T luni]" la un depozit / cont de economii
      -> nominala, categoria 'depozite', termenul în `frecventa`
  - „dobândă … X%" / „DAE … X%" la un credit -> nominala / dae, 'credite'
      (azi niciun rând din catalog nu are așa ceva; regula e pentru exporturile
       următoare și e acoperită de test)

Scrierea trece prin fluxul comun (`normalizeaza.brut` + `normalizeaza.scrie`) cu
`metoda_extractie = 'catalog'`, pe o sursă dedicată fișierului Excel
(tip_sursa 'document', format 'xlsx', rol 'conditii'). Idempotent: `scrie`
șterge întâi ce a scris metoda 'catalog' la Libra, apoi inserează.

Ascunderea valorilor web înlocuite NU se face aici, ci în vederea
`observatii_curente` (migrarea 022, db/sincronizeaza_vederi.sql): o refacere
din Bronze recreează observațiile colectate, iar regula trebuie să rămână
valabilă; nimic nu se șterge din `observations`.

ATENȚIE: `populare_initiala.py --de-la-zero` golește TOATĂ tabela observations
și sursele de tip 'document', deci și valorile de aici. După o astfel de rulare
se reia acest script (`--din-bronze` nu le atinge: șterge doar 'populare').

Rulare:
    python ingest/catalog_libra_valori.py            # extrage + scrie
    python ingest/catalog_libra_valori.py --uscat    # doar raportul, fără scriere
"""

import argparse
import collections
import os
import re
import sys

import psycopg2
import psycopg2.extras

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import normalizeaza as N           # noqa: E402

BANCA = "libra"
METODA = "catalog"

# segmentul din catalog -> segmentele din cod_scenariu. PF+PJ înseamnă că
# prețul e declarat pentru AMÂNDOUĂ, deci se marchează ambele (nu „nemarcat":
# matricea ar afișa atunci „segment nemarcat în sursă", ceea ce ar fi fals).
SEGMENT = {"PF": "pf", "PJ": "pj", "PF+PJ": "pf|pj"}

# produsele de cont: doar la ele „Abonament X lei/lună" e prețul pachetului de cont
CATEGORII_CONT = {"CONT_CURENT", "CONT_OPERATIUNI"}

NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"
MULT = r"(?:\s*(?:mil\.|k)(?![a-zăâîșț]))?"

# „Abonament 29 lei/lună", „Abonament corporate 225 lei/lună",
# „Abonament operațional 50 lei/lună" — un singur cuvânt descriptiv, opțional
RE_ABONAMENT = re.compile(
    rf"\bAbonament(?:\s+[a-zăâîșț]+)?\s+(?P<v>{NUM})\s*lei\s*/\s*lun[ăa]\b", re.I)

RE_DOBANDA = re.compile(r"\bdob[âa]nd[ăa]\b", re.I)
RE_DAE = re.compile(r"\bDAE\b")
# un element de listă după „dobândă": „~3,00% p.a. la 6-12 luni", „2,00% nelimitat",
# „~6,60%/6,10% p.a." (pereche -> ambiguă)
RE_ITEM_RATA = re.compile(
    rf"(?P<aprox>~)?(?P<v>{NUM})\s*%(?P<pereche>\s*/\s*~?(?:{NUM})\s*%)?"
    r"(?:\s*p\.\s?a\.)?"
    r"(?:\s+(?:la\s+)?(?P<termen>\d+(?:\s*[-–]\s*\d+)?\s+luni)\b|\s+(?P<nelimitat>nelimitat))?")
RE_TERMEN_PRODUS = re.compile(r"\b(\d+)\s+luni\b")

# toate cifrele care arată a preț, ca raportul să spună ce N-a fost mapat
RE_PROCENT = re.compile(rf"~?(?:{NUM})\s*%?(?:\s*[–/-]\s*~?(?:{NUM}))?\s*%")
RE_SUMA = re.compile(
    rf"~?(?:{NUM})(?P<m1>{MULT})(?:\s*[–-]\s*~?(?:{NUM})(?P<m2>{MULT}))?"
    r"(?P<cur>\s*(?:lei|RON|EUR|euro)\b)?", re.I)
RE_GRATUIT = re.compile(r"[^,.;:]{0,40}\b(?:gratuit\w*|f[ăa]r[ăa]\s+costuri)\b[^,.;:]{0,40}", re.I)


def _num(s):
    return float(s.replace(".", "").replace(",", "."))


def _termen_produs(text, denumire):
    """Termenul produsului, dacă e scris și e unul singur („pe 7 luni").

    Două termene diferite în același text -> None: nu se ghicește care e al
    dobânzii (termenul rămâne „nespecificat" în pagina Rate).
    """
    gasite = {int(m.group(1)) for sursa in (text, denumire or "")
              for m in RE_TERMEN_PRODUS.finditer(sursa)}
    return f"{gasite.pop()} luni" if len(gasite) == 1 else None


def _categorie_rata(cod):
    if cod == "DEPOZITE":
        return "depozite"
    if (cod or "").startswith("CREDIT_"):
        return "credite"
    return None


def _motiv(text, a, b, fragment):
    """De ce o cifră rămâne nemapată. Motivul intră în raport, nu în bază."""
    inainte = text[max(0, a - 45):a].lower()
    dupa = text[b:b + 25].lower()
    # ordinea contează: „fără garanții până la 70.000 lei" e o limită, nu o
    # garanție; „max. 70.000 lei), dobândă doar pe…" e tot o limită
    if "mpos" in inainte[-12:]:
        return "procent mPOS: textul nu spune ce comision e (per tranzacție? minim?)"
    if "avans" in inainte:
        return "avans minim, nu dobândă"
    if (re.search(r"(max\.|min\.|până la|pana la|peste|valoare)[^;,:%]{0,25}$", inainte)
            or dupa.lstrip().startswith("din ")):
        return "limită / prag (sumă finanțată, plafon, sold), nu preț"
    if "garan" in inainte[-20:]:
        return "procent de garantare, nu dobândă"
    if RE_DOBANDA.search(dupa[:12]) or RE_DOBANDA.search(inainte[-12:]):
        return ("dobândă la sold (card/cont): în bază stă în aceeași categorie "
                "(conturi_carduri) cu dobânda cardului de credit, pe care catalogul "
                "n-o dă — mapată, ar ascunde-o")
    if dupa.startswith("/an"):
        return "sumă anuală fără denumirea comisionului (emitere? administrare?)"
    if re.search(r"[–-]|mil\.|\dk", fragment):
        return "interval / plafon de finanțare, nu preț"
    return "cifră fără serviciu numit"


def extrage(produs):
    """Un rând din catalog_libra -> (valori brute pentru normalizeaza, nemapate).

    `produs` e un dict cu cheile tabelei (cod, denumire, categorie, categorie_cod,
    segment, caracteristici, fisier, foaie, rand). Fără bază de date, testabil.
    """
    text = produs.get("caracteristici") or ""
    cod_cat = produs.get("categorie_cod")
    segment = SEGMENT.get(produs.get("segment"))
    comun = dict(
        banca=BANCA, sursa=produs["fisier"], tip_sursa="document", format="xlsx",
        # 'conditii', nu 'produs': e o listă de prețuri, nu pagina web a unui
        # produs; și, mai ales, `scrie` NU șterge niciodată observațiile Libra
        # de pe surse 'produs' (le protejează fiindcă nu se mai colectează),
        # deci cu 'produs' rerularea ar dubla valorile.
        rol_sursa="conditii", frecventa_sursa="manual",
        serviciu=produs["denumire"], sectiune=produs.get("categorie"),
        segment=segment, incredere="ridicata",
    )
    valori, nemapate, consumat = [], [], []

    def liber(a, b):
        """Cifra din [a, b) n-a fost deja folosită de o regulă."""
        return not any(x < b and a < y for x, y in consumat)

    def nemapat(fragment, motiv):
        nemapate.append({"cod": produs["cod"], "fragment": fragment.strip(), "motiv": motiv})

    # --- abonamentul pachetului de cont
    for m in RE_ABONAMENT.finditer(text):
        consumat.append(m.span("v"))
        if cod_cat not in CATEGORII_CONT:
            nemapat(m.group(0), f"abonament la un produs care nu e de cont ({cod_cat})")
            continue
        valori.append(N.brut(**comun, concept="administrare_cont", tip="comision_suma",
                             valoare=_num(m.group("v")), moneda="LEI", frecventa="lunar",
                             categorie="comision", citat=m.group(0)))

    # --- dobânzile: doar în clauza care începe cu „dobândă" / „DAE"
    cat_rata = _categorie_rata(cod_cat)
    if cat_rata:
        for m in list(RE_DOBANDA.finditer(text)) + list(RE_DAE.finditer(text)):
            concept = "dae" if m.group(0) == "DAE" else "nominala"
            # clauza se termină la „;" sau la punctul de final de frază
            # (nu la „p.a." sau „max.")
            fin = re.search(r";|\.(?=\s+[A-ZĂÂÎȘȚ]|\s*$)", text[m.end():])
            clauza_fin = m.end() + (fin.end() if fin else len(text) - m.end())
            poz, primul = m.end(), True
            for it in RE_ITEM_RATA.finditer(text, m.end(), clauza_fin):
                # între două elemente ale listei stă doar un separator sau o
                # legătură scurtă („la sold zilnic: "); altfel nu mai e lista dobânzii
                legatura = text[poz:it.start()]
                if len(legatura) > (40 if primul else 3) or not liber(*it.span("v")):
                    break
                consumat.append(it.span("v"))
                citat = text[m.start():it.end()] if primul else it.group(0)
                if it.group("pereche"):
                    consumat.append((it.start("pereche"), it.end("pereche")))
                    nemapat(citat, "două dobânzi fără variantă (care e pentru cine / ce monedă?)")
                else:
                    termen = it.group("termen") or it.group("nelimitat")
                    if termen:
                        termen = re.sub(r"\s*[-–]\s*", "-", termen)
                    else:
                        termen = _termen_produs(text, produs.get("denumire"))
                    detaliu = [x for x, da in (
                        ("aproximativ („~” în catalog)", it.group("aprox")),
                        ("valoare minimă („de la” în catalog)", primul and "de la" in legatura),
                    ) if da]
                    valori.append(N.brut(
                        **comun, concept=concept, tip="rata", valoare=_num(it.group("v")),
                        frecventa=termen, categorie=cat_rata, citat=citat,
                        detaliu="; ".join(detaliu) or None))
                poz, primul = it.end(), False

    # --- restul cifrelor: raportate, nemapate
    for m in RE_PROCENT.finditer(text):
        if liber(*m.span()):
            consumat.append(m.span())
            nemapat(m.group(0), _motiv(text, *m.span(), m.group(0)))
    for m in RE_SUMA.finditer(text):
        if not (m.group("cur") or m.group("m1") or m.group("m2")) or not liber(*m.span()):
            continue
        consumat.append(m.span())
        nemapat(m.group(0), _motiv(text, *m.span(), m.group(0)))
    for m in RE_GRATUIT.finditer(text):
        nemapat(m.group(0), "gratuitate fără sumă scrisă: nu se transformă în „0 lei”")
    return valori, nemapate


def citeste_catalog(cur, fisier=None):
    """Rândurile catalogului; implicit ale ultimului fișier importat."""
    if not fisier:
        cur.execute("""SELECT fisier FROM catalog_libra c JOIN banci b ON b.id = c.id_banca
                       WHERE b.slug = %s ORDER BY importat_la DESC LIMIT 1""", (BANCA,))
        rand = cur.fetchone()
        if not rand:
            raise SystemExit("catalog_libra e goală: rulează întâi ingest/load_catalog_libra.py")
        fisier = rand["fisier"]
    cur.execute("""SELECT c.cod, c.denumire, c.categorie, c.categorie_cod, c.segment,
                          c.caracteristici, c.fisier, c.foaie, c.rand
                   FROM catalog_libra c JOIN banci b ON b.id = c.id_banca
                   WHERE b.slug = %s AND c.fisier = %s ORDER BY c.rand""", (BANCA, fisier))
    return [dict(r) for r in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fisier", help="numele fișierului din catalog_libra (implicit ultimul importat)")
    ap.add_argument("--uscat", action="store_true", help="doar raportul; nu scrie nimic")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import config
    config.incarca()
    with psycopg2.connect(N.dsn()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            produse = citeste_catalog(cur, a.fisier)

    brute, nemapate = [], []
    for p in produse:
        v, n = extrage(p)
        brute += v
        nemapate += n
    print(f"{len(produse)} produse din „{produse[0]['fisier']}”: "
          f"{len(brute)} valori mapate, {len(nemapate)} cifre nemapate\n")
    for b in brute:
        print(f"  MAPAT  {b['concept']:18} {b['valoare']:>8g} {b.get('frecventa') or '':10} "
              f"{b['categorie']}|{b['segment'] or '-'}  {b['serviciu']}  ❝{b['citat']}❞")
    print()
    for n in nemapate:
        print(f"  NEMAPAT {n['cod']:24} ❝{n['fragment']}❞  — {n['motiv']}")

    if a.uscat:
        print("\n--uscat: nu s-a scris nimic.")
        return 0
    raport = collections.Counter()
    randuri = [r for r in (N.normalizeaza(b, raport) for b in brute) if r]
    if randuri:
        N.scrie(randuri, METODA, raport, banci=[BANCA])
    else:
        # `scrie` iese devreme pe listă goală, fără să șteargă; fără asta,
        # valorile unui export anterior ar rămâne în bază
        raport["observatii_sterse"] += N.curata(METODA, [BANCA])
    N.raporteaza(raport, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
