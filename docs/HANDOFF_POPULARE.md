# Handoff: popularea de la zero (23–24.09.2026)

Pentru cine lucrează mai departe pe MIP după acest push. Citește-l o dată,
de sus în jos, înainte să rulezi ceva.

## Ce s-a schimbat, pe scurt

Baza nu se mai populează din pachetele JSON (`date/pachet/`) și nici din
`router.py`. Există un singur punct de intrare, `ingest/populare_initiala.py`,
care urmează flow-ul din `docs/arhitectura-flow.html`:

```
descoperire (ingest/descoperire.py)  → scrie DOAR în `surse`
   sitemap ∪ navigare pe 2 niveluri ∪ paginile „tarife / documente"
extracție   (ingest/populare_initiala.py) → citește `surse`, scrie `observations`
   robots.txt → requests cu crawler.UA → Playwright doar pentru pagini JS
   STOP la 401/403/429 sau pagină de blocaj: banca e documentată ca blocată
   amprentă pe textul sanitizat → Bronze doar la schimbare
   parserele din crawler/ → LLM doar pe liniile nereușite (opțional)
   validator.py pe dobânzi → normalizare + deduplicare → observations
```

Detaliile, cu cifrele înainte/după: `docs/IMBUNATATIRI.md`.
Designul și planul: `docs/superpowers/specs/` și `docs/superpowers/plans/`.

## Ce ai de făcut după `git pull`

```bash
pip install -r requirements.txt          # a apărut duckdb (harta Overture)
playwright install chromium              # dacă nu e deja

# migrările noi, în ordine
for n in 013_stare_viitor 014_locatii_overture 015_coloana_locator \
         016_retea_partener 017_app_store_pagina; do
  docker exec -i mip-db psql -U mip -d mip < db/migration_$n.sql
done
docker exec -i mip-db psql -U mip -d mip < db/sincronizeaza_vederi.sql
```

**Atenție la migrarea 017:** șterge toate recenziile din `app_review`. Veneau
din feed-ul RSS Apple, pe care robots.txt îl interzice (`Disallow: /*/rss/*`).
Recenziile se reiau cu `python ingest/load_mobil.py`, de pe pagina publică.

**Numerotare:** migrările ocupă acum 013–017. Următoarea e 018.

## Cum rulezi

```bash
# totul de la zero: golește observațiile + inventarul web, arhivează Bronze
python ingest/populare_initiala.py --de-la-zero --paralel 6

# o singură bancă, cap-coadă (descoperire + descărcare + extracție)
python ingest/populare_initiala.py --banca vista

# descoperă din nou și descarcă DOAR sursele noi, apoi reface banca din Bronze
python ingest/populare_initiala.py --banca bcr --completeaza

# refă extracția din Bronze, fără nicio cerere la bănci
# (după o schimbare de parser: exact ce trebuie rulat)
python ingest/populare_initiala.py --din-bronze --paralel 6

# oricare dintre ele + rezerva LLM (costă; răspunsurile intră în cache)
... --llm-rezerva
```

Alte scripturi:

| script | ce face |
|---|---|
| `ingest/descoperire_llm.py --banca X [--scrie]` | caută prin Anthropic doar produsele fără sursă; sare băncile blocate; costul se afișează |
| `ingest/load_mobil.py` | App Store: versiune, rating, distribuție pe stele, recenzii (pagina publică) |
| `ingest/load_locatii_overture.py` | harta: sucursale și ATM-uri din Overture Maps |
| `ingest/locatoare_js.py` | locatoarele băncilor încărcate prin JavaScript (0 puncte deocamdată) |
| `scripts/raport_calitate.py` | cât din date e „curat", pe bancă, cu citatele verificate în sursă |

Nu rula două rulări pe aceeași bancă deodată: ambele înlocuiesc observațiile
băncii la final, iar ultima câștigă.

## Reguli noi, pe care să nu le strici

- **Blocaj = stop.** La 401/403/407/429/451 sau o pagină „Access denied" (cod
  200 cu pagină aproape goală), sursa devine `status='blocat'`. Nu se încearcă
  Playwright, LLM sau alt canal. Bănci blocate acum: BT, CEC, Intesa,
  UniCredit, Revolut.
- **Un singur UA**, `crawler.UA`, peste tot (requests, Playwright, proxy `/pdf`).
- **robots.txt și după redirect**, și pe proxy-ul `/pdf`.
- **Documentele fără tarife nu dau prețuri**: rapoarte Reg. 575, situații
  financiare, buletine economice, API PSD2, asigurări, prospecte
  (`extractoare.RE_NU_TARIF`). Au dat ~9.000 de valori false înainte de filtru.
- **Dobânzile din HTML se iau doar din conținutul principal**, nu din meniu
  sau subsol (31% din citate veneau de acolo).
- **Tot ce propune LLM-ul merge în coada de verificare** (`ambiguu = true`),
  nu direct în comparații.
- **ATM-urile altei rețele** (Euronet la Patria) sunt `retea = 'partener'`,
  nu rețeaua băncii.

## Ce s-a unit din munca voastră (24.09)

- Parserele PDF ale colegului (subpuncte cu serviciu, USD/GBP/CHF, valori
  false scoase, dobânzile din listele de tarife) sunt cele din repo.
- Vocabular: `refuz_plata` și prețul pachetului pe `administrare_cont` sunt
  ale colegului; dublurile noastre au fost scoase. Rămâne doar
  `recuperare_card` adăugat de noi.
- `load_appstore.py` e șters: îl înlocuiește `load_mobil.py`, care face deja
  „doar magazinul românesc".
- `scripts/test_validare.py`: 204/204.

## Ce rămâne deschis

1. **ROBOR/IRCC**: tabela `indici_referinta` are încă datele din pachetul din
   21.09; de colectat de la zero de pe bnr.ro (fără IRCC deocamdată), plus
   cursul BNR din feed-ul XML oficial.
2. **Concept comparabil ~59%**: cea mai mare pârghie pentru paginile 2.1/2.2.
3. **Dobânzile din PDF-urile de dobânzi** (BCR, BRD, tbi) trec prin parserul
   de tarife; ar trebui prin cel de dobânzi, ca să apară la 2.2.
4. **Băncile blocate**: doar pe o cale aprobată (comparator public, cerere de
   acces, aviz juridic).
5. **Locatoarele cu căutare** (BCR, BRD…): API-ul hărții e interzis de
   robots.txt la BRD, CreditCoop, Libra.
