#!/usr/bin/env bash
# Fluxul nou pe produsele din 2.1, pe 25 de bănci (fără cele 5 blocate de jurnalul echipei): discovery,
# apoi extragere, câte 7 bănci odată. Perechile refăcute la testul din 12.10 dimineața se sar.
cd "$(dirname "$0")/../../extragere_produse_bancare" || exit 1
L=../loguri/flux_21_20261012
TOATE=CONT_ONLINE_PERSONAL,CONT_ONLINE_BUSINESS,ABONAMENT_PFA,CARD_DEBIT_FREE,CARD_DEBIT_GOLD,CARD_DEBIT_BUSINESS,ROPAY
REST=ABONAMENT_PFA,CARD_DEBIT_GOLD,CARD_DEBIT_BUSINESS,ROPAY
BANCI="bcr brd ing raiffeisen garanti exim libra vista patria procredit tbi salt citibank bnpparibas creditcoop bid bankofchina credex techventures brci bcr-locuinte nexent cetelem banorient pko"
produse() {
  case "$1" in
    bcr) echo "$REST,CARD_DEBIT_FREE" ;;
    brd|ing|raiffeisen|garanti|exim|libra) echo "$REST" ;;
    *) echo "$TOATE" ;;
  esac
}
export -f produse; export L TOATE REST
unset ANTHROPIC_API_KEY
faza() {  # $1 = discovery | extragere
  for b in $BANCI; do echo "$b"; done | xargs -P 7 -I{} bash -c '
    p=$(produse {})
    if [ "'"$1"'" = discovery ]; then
      PYTHONIOENCODING=utf-8 python descopera_surse_libra.py --banca {} --produse "$p" --forteaza > $L/discovery_{}.log 2>&1
    else
      PYTHONIOENCODING=utf-8 python extrage_comparatie_libra.py --banca {} --produse "$p" --forteaza --paralel 3 > $L/extragere_{}.log 2>&1
    fi
    echo "'"$1"' {} gata, cod $?" >> $L/_stare.txt'
}
faza discovery
echo "=== discovery terminat" >> $L/_stare.txt
faza extragere
echo "=== extragere terminată" >> $L/_stare.txt
