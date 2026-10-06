#!/usr/bin/env bash
# Aplicația Libra Bank (APLICATIA_LIBRA): discovery pe toate băncile simultan, apoi extracția (Cetelem: WAF real, se sare).
cd "$(dirname "$0")/../../extragere_produse_bancare"
export PYTHONIOENCODING=utf-8
P=APLICATIA_LIBRA
L=../loguri/aplicatie
BANCI="banca-transilvania bankofchina banorient bcr bcr-locuinte bid bnpparibas brci brd cec citibank credex creditcoop exim garanti ing intesa libra nexent patria pko procredit raiffeisen revolut salt tbi techventures unicredit vista"
echo "ETAPA 1 discovery: $(date +%H:%M:%S)"
for b in $BANCI; do
  ( python descopera_surse_libra.py --banca "$b" --produse $P --forteaza > "$L/$b.discovery.log" 2>&1; echo "discovery $b: cod $?" ) &
done
wait
echo "ETAPA 2 extractie: $(date +%H:%M:%S)"
for b in $BANCI; do
  ( python extrage_comparatie_libra.py --banca "$b" --produse $P --forteaza --paralel 10 > "$L/$b.extractie.log" 2>&1; echo "extractie $b: cod $?" ) &
done
wait
echo "GATA toate: $(date +%H:%M:%S)"
