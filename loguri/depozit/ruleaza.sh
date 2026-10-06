#!/usr/bin/env bash
# Depozit la termen, din nou, pe 29 de bănci simultan (Cetelem: WAF real, se sare).
cd "$(dirname "$0")/../../extragere_produse_bancare"
export PYTHONIOENCODING=utf-8
BANCI="banca-transilvania bankofchina banorient bcr bcr-locuinte bid bnpparibas brci brd cec citibank credex creditcoop exim garanti ing intesa libra nexent patria pko procredit raiffeisen revolut salt tbi techventures unicredit vista"
for b in $BANCI; do
  (
    python descopera_surse_libra.py --banca "$b" --produse DEPOZIT_TERMEN --forteaza > "../loguri/depozit/$b.discovery.log" 2>&1
    echo "discovery $b: cod $?"
    python extrage_comparatie_libra.py --banca "$b" --produse DEPOZIT_TERMEN --forteaza > "../loguri/depozit/$b.extractie.log" 2>&1
    echo "extractie $b: cod $?"
  ) &
done
wait
echo "GATA toate"
