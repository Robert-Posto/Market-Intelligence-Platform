#!/usr/bin/env bash
# Depozit la termen, grila structurată: întâi discovery pe toate băncile simultan,
# apoi extracția pe toate simultan (Cetelem: WAF real, se sare).
cd "$(dirname "$0")/../../extragere_produse_bancare"
export PYTHONIOENCODING=utf-8
L=../loguri/depozit2
BANCI="banca-transilvania bankofchina banorient bcr bcr-locuinte bid bnpparibas brci brd cec citibank credex creditcoop exim garanti ing intesa libra nexent patria pko procredit raiffeisen revolut salt tbi techventures unicredit vista"
echo "ETAPA 1 discovery: $(date +%H:%M:%S)"
for b in $BANCI; do
  ( python descopera_surse_libra.py --banca "$b" --produse DEPOZIT_TERMEN --forteaza > "$L/$b.discovery.log" 2>&1; echo "discovery $b: cod $?" ) &
done
wait
echo "ETAPA 2 extractie: $(date +%H:%M:%S)"
for b in $BANCI; do
  ( python extrage_comparatie_libra.py --banca "$b" --produse DEPOZIT_TERMEN --forteaza --paralel 10 > "$L/$b.extractie.log" 2>&1; echo "extractie $b: cod $?" ) &
done
wait
echo "GATA toate: $(date +%H:%M:%S)"
