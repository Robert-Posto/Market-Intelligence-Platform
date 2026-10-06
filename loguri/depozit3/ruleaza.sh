#!/usr/bin/env bash
# Doar extracția Depozit la termen, după reparațiile din rezolva / _luni / citat (sursele din discovery-ul de la 13:51).
cd "$(dirname "$0")/../../extragere_produse_bancare"
export PYTHONIOENCODING=utf-8
L=../loguri/depozit3
BANCI="banca-transilvania bankofchina banorient bcr bcr-locuinte bid bnpparibas brci brd cec citibank credex creditcoop exim garanti ing intesa libra nexent patria pko procredit raiffeisen revolut salt tbi techventures unicredit vista"
echo "START extractie: $(date +%H:%M:%S)"
for b in $BANCI; do
  ( python extrage_comparatie_libra.py --banca "$b" --produse DEPOZIT_TERMEN --forteaza --paralel 10 > "$L/$b.extractie.log" 2>&1; echo "extractie $b: cod $?" ) &
done
wait
echo "GATA toate: $(date +%H:%M:%S)"
