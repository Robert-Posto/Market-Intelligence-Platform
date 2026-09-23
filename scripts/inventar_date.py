"""Ce formulari de data folosesc bancile, de fapt — inainte de a scrie regexul.

Rulare:  python scripts/inventar_date.py
Ieșire:  output/inventar_date.json  +  tiparele cele mai frecvente la consola

De ce exista: prima versiune a lui `crawler/data_document.py` a fost scrisa din
cap, pe ce mi se parea ca scriu bancile. Inventarul asta, peste toate cele 808
documente, a gasit trei feluri in care ea ar fi produs date GREȘITE:

  "valabil PANA LA 30.09.2026"  — data de sfarsit luata drept inceput
  "cerere depusa incepand cu 15 iulie 2026"  — o conditie din corp, nu data actului
  "versiunea 12", "versiunea v_1.4"  — numar de versiune, nu data

Si doua forme pe care nu le acopeream deloc: campul "Data:" din formularul
standardizat, si lunile prescurtate ("oct.2024").

Se rulează din nou cand se adauga banci noi sau cand acoperirea datelor scade.
Nu e in lantul de dupa crawl: e o unealta de calibrare, nu un pas de productie.
"""
import sys, re, json, collections
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pdfplumber

PDFURI = Path('output/crawl/pdf')
# orice linie care vorbeste despre valabilitate SI contine o cifra
RE_INTERES = re.compile(r'(vigoare|valabil|aplicabil|incep[aâ]nd|[îi]ncep[aâ]nd|actualizat|versiun|edi[tț]i)', re.I)
RE_CIFRA = re.compile(r'\d')

linii = collections.Counter()
per_doc = {}
fisiere = sorted(PDFURI.rglob('*.pdf'))
print('documente:', len(fisiere), flush=True)
for i, f in enumerate(fisiere):
    if i % 100 == 0: print('  ...%d' % i, flush=True)
    try:
        with pdfplumber.open(f) as pdf:
            t = '\n'.join((p.extract_text() or '') for p in pdf.pages[:2])
    except Exception as e:
        per_doc[str(f)] = {'eroare': str(e)[:60]}
        continue
    gasite = [l.strip() for l in t.splitlines()
              if RE_INTERES.search(l) and RE_CIFRA.search(l)]
    per_doc[str(f)] = {'linii': gasite[:6]}
    for l in gasite[:6]:
        linii[re.sub(r'\d', '#', l.lower())[:110]] += 1

json.dump(per_doc, open('output/inventar_date.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\ndocumente cu cel putin o linie de valabilitate: %d din %d'
      % (sum(1 for v in per_doc.values() if v.get('linii')), len(per_doc)))
print('\nCELE MAI FRECVENTE TIPARE (cifrele inlocuite cu #):')
for l, n in linii.most_common(45):
    print('%4d  %s' % (n, l))
