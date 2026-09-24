"""Vocabularul canonic de servicii bancare, pentru comparatia intre banci.

De ce e nevoie de el: Legea 258/2017 standardizeaza STRUCTURA formularului, nu
formularea. Masurat pe cele 16 documente standardizate, doar 4 nume de serviciu
din 116 sunt folosite de 3 banci din 5. Deci comparatia nu se poate face pe textul
denumirii; trebuie o mapare.

Trei axe, nu una. Masurat pe cele 4.356 de comisioane: gruparea pe un singur
cuvant-cheie acopera 66% din volum, dar grupele nu inseamna nimic — "administrar"
aduna administrarea contului, a cardului si a internet bankingului, care au
preturi diferite de un ordin de marime. Gruparea pe doua cuvinte da grupe corecte,
dar acoperirea scade la 33%. Cauza e ca un serviciu nu se identifica prin nume
singur: "retragere numerar" are 140 de valori la 8 banci fiindca amesteca ghiseu,
ATM si POS.

Deci fiecare comision se descrie prin:
  concept    - CE serviciu (retragere_numerar, transfer_credit, ...)
  canal      - PRIN CE se face (ghiseu, atm, pos, internet_banking, ...)
  destinatie - CATRE UNDE merge banii (intrabancar, interbancar, extern, sepa)

Maparea e singurul pas din tot lanțul care nu se poate verifica geometric: daca
"Transfer credit intrabancar" si "Plati intrabancare din aplicatie" sunt acelasi
serviciu depinde de judecata, nu de poziția pe pagina. De aceea fiecare
inregistrare mapata pastreaza denumirea originala, iar ce nu se potriveste rămane
NEMAPAT, nu ghicit.
"""
import re

# Sub atatea caractere, un nume de serviciu e un fragment, nu o denumire (vezi
# nota din canonic()).
LUNGIME_FRAGMENT = 28

# Lungimea singura e un criteriu slab pentru "fragment". Masurat pe cele 1.846 de
# valori nemapate: 1.573 au eticheta care incepe cu litera mica si 180 cu un semn de
# lista — sunt subpuncte ale unui serviciu al carui nume s-a pierdut la granița
# rândului de grila. Multe trec pragul de 28 doar cu un caracter ("- de la ATM-uri
# BCR tranzacție" are 30), deci nu primeau contextul, desi despre ele eticheta nu
# spune nimic. Forma e un criteriu mai bun decat lungimea.
RE_ETICHETA_FRAGMENT = re.compile(
    r"^\s*[-–—•·▪(\[]"                       # semn de lista sau paranteza
    # banda de suma: "≥ 50.000 LEI si urgente (orice suma)" (Vista, 7 valori) nu
    # numeste serviciul, dar trecea de lungime si nu se uita in secțiune
    r"|^\s*[<>≤≥]"
    r"|^[a-zăâîșț]"                          # continuarea unei fraze
    r"|^\s*(?:si|sau|de|la|in|din|pe|pentru|prin|cu)\b", re.I)
# ...dar o nota de subsol nu e un serviciu fara nume, e altceva cu totul. Fara
# excluderea asta, "Nota: pentru optiunea OUR se vor adauga comisioane" primea
# transfer_credit din secțiune — un punct de date inventat. Erau 4 astfel de valori
# in eșantionul de verificare.
RE_ETICHETA_NOTA = re.compile(
    r"^\s*(?:not[ăa]|nota\s+bene|obs|aten[țt]ie|excep[țt]|men[țt]iune)\b\s*[:.]?"
    r"|^\s*[*†‡]|^\s*\d\)\s|^\s*\(\d+\)", re.I)
# Regula de mai sus recunoaște nota numai dupa marcajul din fața ei. Dar o nota
# poate fi si proza curata, fara marcaj: Salt explica pachetele prin "Toate
# pachetele includ serviciile de baza asociate contului curent.", iar din secțiunea
# "ÎNCASARI SI PLATI" cele trei preturi de pachet (0 / 360 / 960 Lei) primeau
# conceptul "incasare" — pretul abonamentului raportat drept comision de incasare.
#
# O fraza intreaga NU e un fragment: un fragment e o bucata dintr-un nume de
# serviciu, care are nevoie de context ca sa se completeze, iar o propoziție cu
# punct final isi spune singura sensul. Daca nu se potrivește pe vocabular de una
# singura, inseamna ca nu descrie un serviciu — nu ca serviciul e scris mai sus.
#
# Masurat pe tot corpusul: 24 de valori au eticheta-fraza, 9 dintre ele erau mapate,
# iar 8 din cele 9 au potrivire DIRECTA pe eticheta (BCR "Pachetul Servicii de Baza
# pentru persoane nevulnerabile...", Garanti "interogare sold ATM GARANTI BANK
# S.A.", Raiffeisen "Acreditive documentare accesand urmatorul link: SEPA
# countries.") si nu sunt atinse, fiindca regula taie numai recursul la context.
RE_ETICHETA_FRAZA = re.compile(r"\w\s*\.\s*$")
CUVINTE_FRAZA = 5


# Eticheta care isi numeste singura serviciul, dar unul fara concept in vocabular,
# nu e fragment si nu ia conceptul secțiunii. Sub "PLATI", "Investigatii
# telefonice/ email/ SWIFT" (Vista, "Maxim 15 EUR") intra la transfer_credit si
# strica linia plafoanelor de transfer (dispersie interna 60x).
# "Confirmare" simplu nu intra aici: sub "ACREDITIVE" e confirmarea acreditivului,
# serviciu documentar (13 valori), la fel investigarea documentelor de incasso.
RE_SERVICIU_FARA_CONCEPT = re.compile(
    r"^\W*(?:speze\s+pentru\s+|comision\s+(?:de\s+|pentru\s+)?)?investiga[țt]"
    r"(?![^.]{0,40}document)"
    r"|^\W*(?:eliberare\s+)?(?:adeverin[țt]|confirm\w*\s+(?:sold|audit)|duplicat"
    r"|scriso(?:are|ri)\s+de\s+(?:bonitate|recomandare|inten))"
    r"|^\W*(?:[îi]nchirier\w*\s+)?caset|^\W*curierat", re.I)


def _e_fragment(nume):
    """Eticheta nu spune singura despre ce serviciu e vorba."""
    if RE_ETICHETA_NOTA.search(nume):
        return False        # nota de subsol: nu se mapeaza deloc
    if RE_SERVICIU_FARA_CONCEPT.search(nume):
        return False        # isi numeste serviciul, doar ca vocabularul nu il are
    if RE_ETICHETA_FRAZA.search(nume) and len(nume.split()) >= CUVINTE_FRAZA:
        return False        # proza fara marcaj: tot nota, doar nemarcata
    return len(nume) < LUNGIME_FRAGMENT or bool(RE_ETICHETA_FRAGMENT.search(nume))

# "cont de plăți" e termenul legal pentru contul curent (transpunerea directivei
# PAD), nu o plata. Se scoate din text INAINTEA potrivirii, altfel "La ghișeu din
# contul de plăți" — care e o retragere de numerar — primea transfer_credit de la
# cuvantul "plăți". Un lookbehind nu merge: are nevoie de lațime fixa.
RE_CONT_DE_PLATI = re.compile(r"cont\w*\s+de\s+pl[ăa][țt]i", re.I)
# Eticheta care isi enumera continutul e pachetul, nu primul serviciu din lista:
# "George, conţinȃnd: - administrarea Cont curent; - furnizarea unui Card..." dadea
# emitere_card la 16 preturi de pachet BCR (12-1.200 lei). Conceptul se cauta doar
# in capul etichetei. "ȃ" (a cu breve inversat) e chiar litera din document.
RE_LISTA_CONTINUT = re.compile(r",?\s*(?:con[țt]in[âaȃ]nd|const[ăa]\s+[îi]n)\b.*",
                               re.I | re.S)

# Ordinea conteaza, si regula e: SUBSTANTIVUL-CAP decide. "Încasare interbancara
# prin ordin de plata" e o incasare, nu un ordin de plata; "Anulare ordin de plata"
# e o anulare; "Plată/negociere/manipulare documente" e serviciu documentar. Prima
# versiune avea transfer_credit inaintea lor si le inghitea pe toate trei — 901 de
# valori intr-un singur concept, dintre care multe greșite.
RE_PLATA_PROGRAMATA = r"standing\s+order|plat[ăa]\s+programat|ordin\w*\s+programat"
SERVICII = [
    # Alertele SMS inaintea cardului si a contului: substantivul-cap e serviciul de
    # alerta, nu produsul la care e atasat. "Administrare Serviciu Alerte SMS Card"
    # ieșea administrare_card, "Info SMS – încasări și tranzacții cu cardul"
    # incasare, "SMS pentru depăşirea a 25 mesaje" extras_de_cont: 22 de valori in
    # 5 concepte. Anularea serviciului ramane anulare.
    # Doar in capul etichetei: in lista unui pachet ProCredit ("Cont curent în LEI
    # Cont de economii... Serviciul Info SMS") SMS-ul e o componenta, nu serviciul.
    ("alerta_sms", r"^(?!\W*(?:anular|modificar|stornar|dezactivar))[^.]{0,50}?\bSMS\b"),
    # carduri — inaintea celor generale, fiindca "emitere card" nu e "emitere" oarecare
    # "refacere" si "card - reînnoire" (cu cardul inainte) scapau: 5 valori BCR
    ("reemitere_card", r"(reemiter|re-emiter|re[îi]nnoir|[îi]nlocuir|duplicat|refacer)\w*[^.]{0,30}card"
                       r"|card[^.]{0,30}(reemiter|re[îi]nnoir|[îi]nlocuir)"),
    ("emitere_card", r"(emiter|furnizar|eliberar)\w*[^.]{0,30}card"
                     r"|card[^.]{0,25}(emiter|furnizar)"
                     # "Comision de emitere plastic" (Libra, 4 valori)
                     r"|emiter\w*\s+plastic"),
    ("livrare_card", r"(livrar|trimiter|transmiter|curierat)\w*[^.]{0,30}card"
                     r"|card[^.]{0,25}livrar"),
    ("blocare_card", r"blocar\w*[^.]{0,30}card|card[^.]{0,25}blocar"
                     r"|blocare\s+(a\s+)?cardului"),
    ("administrare_card", r"administrar\w*[^.]{0,30}card|card[^.]{0,25}administrar"
                          r"|menten[ăa]n[țt][ăa]|ta?x[ăa]\s+anual[ăa][^.]{0,20}card"
                          # cardul principal/suplimentar, fara cuvantul "card"
                          # (Eximbank: "Administrare lunara" / "Suplimentar")
                          r"|administrar\w*[^.]{0,30}\b(?:principal|suplimentar)\b"),
    ("schimbare_pin", r"\bPIN\b"),
    # comisionul pe tranzacția cu cardul la comerciant, distinct de retragerea
    # de numerar: la EximBank sta sub "COMISIOANE TRANZACTII", la BCR ca
    # "Cumpărare bunuri/servicii"
    ("tranzactie_card", r"cump[ăa]rar\w*[^.]{0,25}(bunuri|servicii)"
                        # Eximbank: "Cumparaturi la comercianti (National/International)"
                        r"|cump[ăa]r[ăa]tur\w*\s+la\s+comercian"
                        r"|tranzac[țt]i\w*\s+(na[țt]ional|interna[țt]ional|quasi)"
                        r"|comisioan\w*\s+tranzac|tranzac[țt]ion\w*\s+comercian"
                        # Libra: "Comision pentru operatiuni la comerciantii din
                        # Romania". Cu "din" obligatoriu, ca sa nu prinda varianta
                        # "la comerciantii de tip jocuri de noroc": gamblingul costa
                        # 1% + 10 lei si ar strica linia platilor obisnuite.
                        r"|opera[țt]iun\w*\s+la\s+comercian\w*\s+din"
                        # "Plăți POS România sau internațional" (Garanti, 4 valori
                        # ieșeau transfer_credit), "Comision tranzacțional Prin
                        # intermediul EPOS" (Raiffeisen, 6), "tranzacţii comerciale"
                        r"|pl[ăa][țt]i\s+(?:la\s+)?E?POS\b"
                        r"|comision\w*\s+tranzac[țt]ional\w*[^.]{0,30}\bE?POS\b"
                        r"|tranzac[țt]i\w*\s+comercial"),
    # numerar
    # "Utilizare ATM/POS de la alte bănci pentru numerar" e tot o retragere
    ("retragere_numerar", r"(retrager|eliberar|ridicar|utilizar)\w*[^.]{0,40}numerar"
                          r"|numerar[^.]{0,20}(retrager|eliberar)"
                          # ...si fara "numerar": BCR "Utilizare ATM-uri Erste
                          # Group***" (8 valori, acelasi pret ca retragerea de la ATM
                          # BCR) lua tranzactie_card din secțiunea "Tranzacţii
                          # Internaţionale". Doar in capul etichetei, si nu la sold/PIN.
                          r"|^\W*(?:comision\s+|cost\s+)?utilizar\w*\s+(?:\(\w+\)\s+)?(?:a\s+)?"
                          r"ATM(?![^.]{0,60}(?:sold|PIN))"
                          # Nexent: "Cost utilizare mijloc de plată la ATM-ul...", "...
                          # prin POS-uri situate la ghișeele bancare" (13 valori)
                          r"|utilizar\w*\s+mijloc\w*\s+de\s+plat[ăa]\s+(?:la|prin)\s+(?:ATM|POS)"
                          # "Retragere de de la ATM-uri si Ghiseele" (Vista, 7)
                          r"|^\W*retrager\w*[^.]{0,15}\b(?:ATM|ghi[șs]e)"),
    ("depunere_numerar", r"depuner\w*[^.]{0,20}numerar|alimentar\w*[^.]{0,20}numerar"),
    # cont
    ("deschidere_cont", r"deschider\w*[^.]{0,25}(cont|depozit)"),
    # pachetul de cont, ca la administrare: "Inchidere pachet" la BRD, 11 valori
    ("inchidere_cont", r"([îi]nchider|lichidar)\w*[^.]{0,25}(cont|pachet)"),
    # BRD nu scrie "administrare": "Pret pachet/luna cu indeplinirea conditiei de
    # pachet" e tot abonamentul lunar al pachetului (22 de valori)
    ("administrare_cont", r"administrar\w*[^.]{0,25}(cont|pachet)"
                          r"|administrare\s+(lunar|anual)|pre[țt]\w*\s+pachet"
                          r"|^\s*administrar\w*\s*$"
                          # ...si numele pachetului singur, cu pretul lui: "Pachet
                          # Gold 0*/30 lei/lună" (Raiffeisen), "Pachet de servicii:
                          # Cost lunar 50 LEI" (ProCredit), 20 de valori nemapate.
                          # Nu componenta: "Pachet • comision de mentenanță".
                          r"|^\W*pachet(?:ul)?\b(?![^.]{0,3}[•\-–])"
                          # ...la fel contul singur: "Cont curent în USD sau GBP: 2
                          # EUR / echivalent, pe cont" (ProCredit), "Cont Curent
                          # Standard 5 lei/lună" (Raiffeisen). Nu dobanda la sold.
                          r"|^\W*(?:•\s*)?cont(?:ul)?\s+curent\b(?![^.;:]{0,70}sold)[^.;:]{0,70}$"),
    # "Extras suplimentar de cont", "Extrase la sediul Bancii" (Vista, 6 valori);
    # nu "Extras ONRC", care e extrasul din registrul comertului
    ("extras_de_cont", r"extras\w*\s+(de\s+)?cont|extras\s+de|stare\s+financiar"
                       r"|extras\w*\s+(?:\w+\s+){1,2}de\s+cont|^\W*extrase\b"),
    # canale la distanta, ca serviciu in sine
    ("administrare_banking_distanta",
     r"administrar\w*[^.]{0,30}(internet|mobile|phone|e-?)\s*banking"
     r"|abonament[^.]{0,25}banking|(internet|mobile)\s*banking\s*[-–]?\s*administrar"
     # Vista: "Accesul prin Internet/Mobile Banking", "... ambele aplicatii (IB+MB)"
     r"|(?:acces|administrar)\w*[^.]{0,40}(?:internet\s*/\s*mobile|\bIB\s*\+\s*MB\b)"
     # Garanti: "Abonament lunar Garanti BBVA Online" (4). Produsul imediat dupa:
     # "Abonament lunar" sub Free-Way (vama, 85 lei/punct) nu e internet banking
     r"|abonament\w*\s+(?:lunar\w*\s+)?(?:\w+\s+){0,2}(?:online|mobile)\b"),
    # cap de expresie mai specific decat "plata" — se verifica INAINTEA lui
    # Vocabularul nu acoperea decat jumatate din serviciile documentare. Cu
    # coborarea la context pentru etichetele-fragment, golul a devenit activ:
    # secțiunile "SGB PRIMITE" si "FINANȚAREA COMERȚULUI" conțin cuvantul "plată",
    # deci 20 de valori ajungeau la `transfer_credit` — 1.500 EUR pentru o cesiune
    # de creanța raportata drept comision de transfer.
    # `scrisoar\w*` NU potrivește pluralul: "scrisoare" -> "scrisori", deci stemul e
    # "scriso". A cincea oara in proiect cand pluralul romanesc nu e un sufix — la
    # fel ca "comision" -> "comisioane". "Eliberare Scrisori de confort" nu se mapa.
    ("documentar", r"acreditiv|incasso|scriso\w*\s+de\s+(?:garan[țt]|confort|credit)"
                   r"|\bSGB\b|aval|remiter\w*[^.]{0,25}document|avizar|negocier"
                   r"|discrepan[țt]|finan[țt]ar\w*\s+(?:a\s+)?comer"
                   r"|cesiun\w*\s+de\s+crean"),
    # Acceptarea cardurilor la comerciant e alt serviciu decat plata cu cardul: banca
    # incaseaza de la comerciant, nu de la client. Doar 8 valori la 2 banci, deci nu
    # va face niciodata o linie in tabel — dar erau 7 mapate greșit pe
    # `transfer_credit`, iar o mapare greșita e mai rea decat una lipsa.
    ("acceptare_carduri", r"acceptare\s+(?:la\s+plat[ăa]\s+a\s+)?cardu"
                          r"|comerciant\w*\s+accept"),
    # "cu încasare venit" e conditia ofertei de credit (salariul virat la banca),
    # nu o incasare: 8 valori BRD
    ("incasare", r"[îi]ncas[ăa]r(?!\w*\s+(?:a\s+)?venit)"),
    # Obiectul refuzului nu e mereu "plata": documentele scriu "Refuz cecuri/ bilete
    # la ordin (neonorate la plata)". Cu vechiul tipar, care cerea "refuz" lipit de
    # "plat", potrivirea cadea pe `transfer_credit` prin "la plata" de la coada —
    # adica un refuz de instrument era raportat drept comision de transfer.
    # "contestare" nu conține "contestaț": 27 de valori BCR "Contestare
    # nejustificată a unei tranzacții" ramaneau nemapate
    # si "refuz la plata": Nexent, "Taxa pentru initiere nejustificata de refuz la
    # plata la ATM/POS", 9 valori care ieseau transfer_credit
    ("refuz_plata", r"refuz\w*\s+(?:de\s+|la\s+)?(?:plat|cec|bilet|instrument|[îi]ncas)"
                    r"|contest(?:a[țt]|ar)|chargeback"
                    # "Comision dispute RoPay pentru fiecare caz" (BRD, 7 valori)
                    r"|\bdisput"),
    ("modificare_anulare", r"^\s*(modificar|anular|stornar)\w*"),
    ("debitare_directa", r"debitar\w*\s+direct|direct\s+debit"),
    ("plata_programata", RE_PLATA_PROGRAMATA),
    ("speze_swift", r"speze\s+swift|mesaj\s+swift|comision\s+swift|ta?x[ăa]\s+swift"),
    # plati. Doua capcane, amandoua gasite la verificarea de mana:
    #  - "cont de plăți" e termenul legal pentru contul curent (PAD), nu o plata.
    #    "La ghișeu din contul de plăți", sub secțiunea "Carduri și numerar", e o
    #    retragere de numerar, si primea transfer_credit de la cuvantul "plăți".
    #  - "plata poliței in 12 rate" e o rata de asigurare, nu un transfer.
    ("transfer_credit", r"transfer\s+credit|ordin\w*\s+de\s+plat[ăa]|\bpl[ăa][țt]i\b"
                        r"|\bplat[ăa]\b(?!\s+(?:poli[țt]|de\s+rambursat))"
                        r"|transfer\w*\s+(de\s+)?bani"
                        r"|vira?ment"
                        # Libra: "sub 50.000 lei urgent prin RTGS" sub "In favoarea
                        # clientilor altor banci"; "clientilor BRCI" poate fi incasare
                        r"|[îi]n\s+favoarea\s+clien\w*\s+altor\s+b[ăa]nci"
                        # "Transferuri intrabancare", "Transfer intre conturi proprii":
                        # formularea Vista, Nexent si Eximbank, fara "credit" si "bani"
                        r"|transfer\w*\s+(?:intra|inter)bancar|transfer\w*\s+[îi]ntre\s+conturi"
                        r"|\btransferuri\b"),
    # diverse cu volum
    ("interogare_sold", r"interog\w*[^.]{0,20}sold|verificar\w*[^.]{0,20}(sold|disponibil)"
                        r"|consultar\w*[^.]{0,20}sold"),
    ("conversie_valutara", r"conversi\w*\s+valutar|schimb\s+valutar"),
    # acelasi concept, dar tiparul neancorat: se incearca abia la sfarsit
    ("modificare_anulare", r"(modificar|anular|stornar)\w*"),
    ("interogare_baze_date", r"\bCIP\b|\bCRB\b|\bRECOM\b|baz[ăa]\s+de\s+date"),
    # sechestrul asigurator e tot o masura de executare pe cont (Vista, 2 valori)
    ("poprire", r"poprir|execut\w*\s+silit|sechestr"),
    # Adăugat pe 23.09.2026: „Taxa recuperare card", 23 de valori nemapate.
    # (Contestarea și prețul pachetului le acoperă deja `refuz_plata` și
    # `administrare_cont`, din vocabularul colegului.)
    ("recuperare_card", r"recuper\w*[^.]{0,30}card|card[^.]{0,30}(re[țt]inut|recuper)"),
    # Ultimele doua, si poziția lor e obligatorie. Instrumentul de plata e OBIECTUL
    # serviciului, nu capul lui: "Remitere la încasare a cecurilor" e o incasare,
    # "Anulare serviciu SMS Alert" e o anulare. Puse mai sus in lista, furau 22 de
    # valori corect mapate. Puse aici, la sfarsit: zero deplasari, 47 de valori
    # castigate. A patra oara in proiect cand ordonarea dupa substantivul-cap decide.
    # si fara "de": "Emitere carnet cec in lei" > "Fila" (Vista, 8 valori)
    ("file_cec", r"file\s+cec|carnet\w*\s+(?:de\s+)?cec|bilet\w*\s+la\s+ordin"
                 r"|\bcec\w*\s+(?:barat|in\s+alb)|formular\w*\s+de\s+cec"
                 r"|instrument\w*\s+de\s+debit|\bcecuri\b"),
    ("alerta_sms", r"\bSMS\s*(?:alert|banking|notific)|alert[ăae]\s+(?:prin\s+)?SMS"
                   r"|notific[ăa]r\w*\s+(?:prin\s+)?SMS|serviciu\s+SMS|\binfo\s*SMS"),
]

# PRIN CE se face operatiunea. Acelasi serviciu costa altfel la ghiseu si la ATM,
# deci fara axa asta am compara lucruri diferite.
CANALE = [
    # Canalele de livrare a unui DOCUMENT, nu de executare a unei operatiuni. Stau
    # primele fiindca sunt mai specifice: "transmitere extras prin SWIFT" conține si
    # cuvinte care ar prinde la ghiseu sau internet banking.
    #
    # De ce trebuie: cele doua masuri de eterogenitate au aratat ca 8 din cele 27 de
    # linii nesigure au fiecare banca consecventa cu ea insasi, dar randul aduna
    # subservicii diferite. Verificat de mana pe extras_de_cont: acolo stau in acelasi
    # rand extrasul lunar (Garanti 8 lei), duplicatul (BRCI 5), varianta pe hartie
    # (Libra 25) si transmiterea prin SWIFT (BCR 100, BRCI 125). Patru lucruri, nu unul.
    ("swift", r"\bswift\b|\bmt\d{3}\b"),
    ("curier_posta", r"curier|po[șs]t[ăa](?!\s+electronic)|expediere"
                     r"|transmitere\s+la\s+adres|adresa\s+indicat"),
    ("hartie", r"suport\s+de\s+h[âa]rtie|pe\s+h[âa]rtie|tip[ăa]rit"),
    # doar formele explicite: "electronic" si "online" singure prind internet banking
    ("email", r"e-?mail|po[șs]t[ăa]\s+electronic"),
    ("atm", r"\bATM\b|\bMFM\b|bancomat|ma[șs]in[ăai]\s+multifunc[țt]"),
    ("pos", r"\bPOS\b|imprinter|\bEPOS\b"),
    ("internet_banking", r"internet\s*banking|\bibank\w*|online|aplica[țt]i"
                         r"|\be-?banking\b|self\s*bank"),
    ("mobile_banking", r"mobile\s*banking|\bMB@?nk|mobil"),
    ("phone_banking", r"phone\s*banking|call\s*cent|care\s*cent|telefon"),
    ("ghiseu", r"ghi[șş]e|casierie|unitate\w*\s+bancar|sucursal|agen[țt]i[ae]"),
]

# Destinatia are sens doar pentru operatiunile care MUTA bani. La o reemitere de
# card nu inseamna nimic, dar se potrivea oricum din numele coloanei ("Națională
# și internațională") si rupea randul tabelului in doua, scazand numarul de banci
# comparabile pe linie.
CONCEPTE_CU_DESTINATIE = {
    "transfer_credit", "incasare", "retragere_numerar", "depunere_numerar",
    "debitare_directa", "plata_programata", "plata_instant", "speze_swift",
    "tranzactie_card", "documentar",
}

# CATRE UNDE merg banii. Diferenta de preț intre intrabancar si extern e mare.
# Ordinea conteaza si e masurata, nu aleasa din instinct. `extern` sta INAINTEA lui
# `ue` fiindca "Plati in afara UE/SEE sau in UE/SEE" conține amandoua formele, iar
# "in afara UE" e sensul care determina prețul. Iar semnalele de rețea proprie stau
# LA URMA, cu acelasi nume ca intrabancar: sunt mai slabe decat cuvantul
# "interbancar". Puse la inceput, stricau 4 atribuiri corecte — "Transfer credit
# interbancar EURO către alte bănci" devenea intrabancar, fiindca undeva in context
# apare "ghișeul băncii".
DESTINATII = [
    ("intrabancar", r"intrabancar|[îi]n\s+cadrul\s+b[ăa]ncii|conturi\s+proprii"
                    r"|acela[șs]i\s+prestator"),
    # Nu toate bancile scriu "SEPA": BRD si BCR scriu definiția pe litere — "tarile
    # care apartin zonei unice de plati in EUR", "Comunitatea Europeană". 16 valori
    # la 3 banci, toate fara destinatie pana acum.
    ("sepa", r"\bSEPA\b|zon[ăa]\s+unic[ăa]\s+de\s+pl[ăa][țt]i"
             r"|zonei\s+unice\s+de\s+pl[ăa]ti|comunitat\w*\s+europe"
             r"|single\s+euro\s+payment"),
    ("extern", r"extern|str[ăa]in[ăa]tate|interna[țt]ional|[îi]n\s+afara\s+UE"
               r"|non[\s-]?UE|transfrontalier"),
    ("interbancar", r"interbancar|alt\s+prestator|alte\s+b[ăa]nci|alt[ei]\s+b[ăa]nci"),
    # "in Uniunea Europeana" si "UE/SEE" nu erau nicaieri: vocabularul avea doar
    # negatia ("in afara UE", "non-UE"). 84 de valori la 5 banci.
    # `\bUE\b` potrivește si in "in afara UE" si in "non-UE", adica exact directia
    # opusa. Cu regula de specificitate (SEPA ⊂ UE ⊂ extern) asta devenea periculos:
    # "Plati in afara UE" dadea {extern, ue} si se rezolva la `ue`. De aceea formele
    # negate sunt excluse explicit — fiecare privire-in-urma are latime fixa, cum
    # cere Python.
    ("ue", r"uniune\w*\s+europe|spa[țt]iul\s+economic"
           r"|(?<!afara\s)(?<!non-)(?<!non\s)\bUE\s*/?\s*SEE\b"
           r"|(?<!afara\s)(?<!non-)(?<!non\s)\bUE\b"),
    # `\bna[țt]ional` NU potrivește in "internațional": inaintea lui e "r", deci nu
    # exista granita de cuvant. La fel `\bintern\b` — "internațional" continua cu "a",
    # care e caracter de cuvant. Verificat, fiindca in proiect granita de cuvant a
    # inșelat deja de trei ori.
    # `\bintern[ae]?\b` prinde si "plati interne", dar NU "internațional": dupa
    # "interna" vine "ț", care e caracter de cuvant, deci granita nu exista.
    ("national", r"\bna[țt]ional\w*\b|\bdomestic\w*|[îi]n\s+Rom[âa]nia"
                 r"|din\s+Rom[âa]nia|\bintern[ae]?\b|\blocal\b"),
    ("intrabancar", r"ATM-?ur\w*\s+(?:BCR|Libra|b[ăa]ncii)"
                    r"|POS-?ur\w*\s+(?:BCR|Libra)|ghi[șs]e\w*\s+b[ăa]ncii"),
]


# ---------------------------------------------------------------------------
# PRODUSE, pentru partea de rate si dobanzi
#
# Aceeasi problema, si mai grava: pe comisioane aveam secțiunile PAD ca axa
# comuna (5 banci din 5, literal). La rate nu exista nicio lege care sa
# standardizeze ceva. Iar campul "produs" din datele de pe web nu e un produs, e
# firimitura de navigație a paginii, cu titlu de marketing inclus:
#   "card de cumparaturi | carduri de credit pentru cumparaturi | bcr persoane fizice"
#   "credit de refinantare fara ipoteca, cu dobanda de la 5,95%"
# Masurat: 185 de bucati distincte, doar 4 folosite de mai mult de o banca.
#
# Ce salveaza situatia: produsele bancare romanesti sunt uniforme ca CONCEPT chiar
# daca fiecare banca le da alt nume comercial. "Expresso" la BRD, "Libra Way" la
# Libra si "creditul Econom" la Patria sunt toate credite de nevoi personale.
# ---------------------------------------------------------------------------
PRODUSE = [
    # programe si produse specifice, inaintea categoriilor generale
    ("noua_casa", r"noua\s+cas[ăa]|prima\s+cas[ăa]"),
    ("refinantare", r"refinan[țt]"),
    ("credit_auto", r"credit\w*[^.]{0,20}(ma[șs]in|auto\b)|ma[șs]in[ăa]\s+electric"),
    ("credit_magazin", r"credit\w*\s+[îi]n\s+magazin|rate\s+la\s+comercian"
                       r"|cump[ăa]r[ăa]ri\s+[îi]n\s+rate"),
    ("descoperit_cont", r"descoperi[rt]\w*\s+de\s+cont|\boverdraft\b"),
    ("credit_nevoi_personale",
     r"nevoi\s+personale|credit\w*\s+de\s+consum|credit\w*\s+personal"
     r"|personal\s+loans?|\bexpresso\b|creditul\s+econom|libra\s+way"
     r"|creditul\s+t[ăa]u\s+personal"),
    # DUPA nevoi_personale, fiindca substantivul-cap decide si aici: "Credit de
    # nevoi personale cu ipotecă" e un credit de nevoi personale garantat, nu un
    # credit ipotecar. Erau 10 valori Patria trecute greșit la ipotecar.
    ("credit_ipotecar", r"ipotec|imobiliar|\bhabitat\b|creditul\s+locativ"
                        r"|credit\w*\s+(pentru\s+)?locuin[țt]"),
    # "finantari europene" a fost scos: nu e un produs, e titlul paginii de
    # navigație pentru persoane juridice a BCR. De la el, un depozit promo cu 5%
    # a fost raportat drept credit pentru business.
    ("credit_business", r"credit\w*[^.]{0,25}(investi[țt]ii|dezvolt[ăa]ri)"
                        r"|credit\w*\s+it\b|credite\s+energie"),
    ("leasing", r"\bleasing\b"),
    # economisire
    ("depozit_termen", r"depozit\w*\s+(la\s+termen|bancar|business|plus|simplu|flexi"
                       r"|fresh|cu\s+depuneri)|\bdeposits?\b|depozitul\b|depozite\b"),
    ("cont_economii", r"cont\w*\s+de\s+economii|economisi|\beconomii\b"
                      r"|savings?\b|deschide\s+cont\s+de\s+economii"),
    ("fonduri_investitii", r"fonduri\s+(mutuale|de\s+investi[țt]ii)"
                           r"|investi[țt]ii\s+la\s+burs"),
    # carduri — cele specifice inaintea celor generale
    ("card_junior", r"card\w*[^.]{0,20}(copii|junior|xteen|\bteen\b)"),
    ("card_salariu", r"card\w*\s+salariu"),
    ("card_cumparaturi", r"card\w*\s+de\s+cump[ăa]r[ăa]turi"
                         r"|card\w*\s+de\s+credit\s*\(\s*cump[ăa]r[ăa]turi"),
    ("card_credit", r"card\w*\s+de\s+credit|carduri\s+de\s+credit|credit\s+cards?"),
    ("card_debit", r"card\w*\s+de\s+debit|debit\s+cards?"),
    # conturi
    ("cont_curent", r"cont\w*\s+curent|current\s+accounts?|cont\s+de\s+pl[ăa][țt]i"
                    r"|pachet\w*\s+(de\s+)?cont|cont\s+bancar|cont\s+imm"
                    r"|business\s+accounts?"),
]

# Segmentul, pentru rate. La comisioane venea din numele documentului; aici din
# firimitura si din categoria paginii.
SEGMENTE_RATE = [
    ("pj", r"persoane\s+juridice|\bIMM\b|\bPFA\b|companii|firm[ăa]|firme"
           r"|business|corporate|profesii\s+liberale|\bSRL\b|for\s+business"),
    ("pf", r"persoane\s+fizice|private\s+individuals"),
]


def _potrivire(lista, text):
    """Prima eticheta din lista care potriveste textul."""
    for nume, tipar in lista:
        if re.search(tipar, text, re.I):
            return nume
    return None


# Documentele scriu diacriticele in doua feluri: cu virgula (ș ț, standardul) si cu
# sedila (ş ţ, din codarile vechi). Tiparele de mai sus sunt scrise cu virgula, asa
# ca "Plăţi interbancare" si "Mentenanţă anuală card" nu se potriveau cu nimic: 20
# de valori BCR si Raiffeisen, plus 15 destinatii. Se normalizeaza textul o data,
# aici, in loc sa se dubleze fiecare [țt] din vocabular.
SEDILA_LA_VIRGULA = str.maketrans("şţŞŢ", "șțȘȚ")


def _curat(text):
    """Sedila la virgula, greseala de tipar cunoscuta, "cont de plăți" -> "cont"."""
    text = str(text or "").translate(SEDILA_LA_VIRGULA)
    # "Administarea contului curent" (Raiffeisen): fara "r", pachetele de sub ea
    # nu erau administrare de cont
    text = re.sub(r"(?i)\badministar", "administrar", text)
    return RE_CONT_DE_PLATI.sub(" cont ", text)


def canonic(inregistrare):
    """(concept, canal, destinatie) pentru un comision, sau (None, ...) daca nu se mapeaza.

    Se caută in tot contextul: numele serviciului, secțiunea de formular, numele
    coloanei din matrice si textul-sursa. Canalul e adesea scris in coloana, nu in
    nume ("Din aplicatia Salt"), iar destinatia in secțiune ("4.2. PLĂȚI > SEPA").
    """
    serviciu = _curat(inregistrare.get("serviciu"))
    nume = RE_LISTA_CONTINUT.sub("", serviciu)
    context = nume + " " + _curat(" ".join(
        str(inregistrare.get(c) or "") for c in
        ("sectiune", "coloana", "detaliu", "text_sursa")))
    concept = _potrivire(SERVICII, nume)
    # Contextul se folosește doar cand numele e un FRAGMENT ("- de la ATM-uri BCR",
    # "tranzacție"): acolo conceptul e legitim in secțiune, fiindca serviciul-parinte
    # s-a pierdut la extragere. Pe un nume intreg, contextul ducea in greșeli —
    # "Activare Garanti BBVA Online fără token" primea transfer_credit, de la
    # cuvantul "plăți" din secțiune.
    if concept is None and _e_fragment(nume):
        # Intai stramosul cel mai apropiat, apoi tot mai sus: sub "ÎNCASĂRI ȘI PLĂȚI
        # > PLĂȚI ÎN ALTE VALUTE", o optiune de plata (Salt, 5 valori) lua incasare
        # doar fiindca incasare sta mai sus in lista decat transfer_credit.
        # Coloana matricei inaintea secțiunii: sub "Alte instrumente de plată",
        # coloana "Debitare directă" e cea care numeste instrumentul (Raiffeisen).
        niveluri = _curat(inregistrare.get("sectiune")).split(" > ")
        coloana = _curat(inregistrare.get("coloana"))
        trepte = [f"{nume} {coloana}"] + [f"{nume} {' > '.join(niveluri[k:])}"
                                          for k in range(len(niveluri) - 1, 0, -1)]
        concept = next(filter(None, (_potrivire(SERVICII, t) for t in trepte)), None)
        if concept is None:
            concept = _potrivire(SERVICII, context)
    # Eticheta care isi enumera continutul e un pachet, iar pretul ei e pretul
    # pachetului, ca la "Pachetul Servicii de Bază, conţinȃnd: ...". Numele
    # pachetului nu spune singur asta: "George, conţinȃnd: - administrarea Cont
    # curent..." (BCR, 12 valori, 12-1.200 lei) ramanea fara concept.
    if concept is None and RE_LISTA_CONTINUT.search(serviciu):
        concept = "administrare_cont"
    # Sub "Standing order (plată programată)", "Plăți - alte conturi" e varianta
    # ordinului programat, nu o plata oarecare: BCR, 4 valori puse la transfer_credit.
    if concept == "transfer_credit" and re.search(
            RE_PLATA_PROGRAMATA, inregistrare.get("sectiune") or "", re.I):
        concept = "plata_programata"
    return concept, _potrivire(CANALE, context), _destinatie(concept, nume, context)


# Construcțiile care numesc EXPLICIT amandoua destinatiile. Comisionul se aplica la
# amandoua, deci nu e nici una, nici alta — si a nu alege e singurul raspuns corect.
# "Națională și" fara continuare intra tot aici: e forma trunchiata a lui "Națională
# și internațională", iar limita de lungime a antetului o taie uneori inainte de
# ultimul cuvant. Masurat: 12 valori BCR primeau `national` pentru un comision de
# cumparare care se aplica si in tara si in afara ei.
RE_AMBELE_DESTINATII = re.compile(
    r"na[țt]ional[ăa]?\s+[șs]i(?:\s+interna[țt]ional\w*)?"
    r"|[îi]n\s*/\s*afara"
    r"|sau\s+ale\s+altor\s+b[ăa]nci"
    # in ambele ordini: "in afara UE/SEE sau in UE/SEE" si invers
    r"|\bUE\s*/?\s*SEE\b[^.;]{0,20}?(?:sau|[șs]i)[^.;]{0,20}?afara"
    r"|afara\s+UE[^.;]{0,25}?(?:sau|[șs]i)[^.;]{0,15}?\bUE\b", re.I)

# Nu orice doua potriviri se contrazic. Geografic ele se cuprind una pe alta:
# SEPA e o parte din UE/SEE, care e o parte din "extern". BRD numeste o plata SEPA
# "Plati EXTERNE catre beneficiari din tarile care apartin ZONEI UNICE de plati in
# EUR" — doua potriviri, dar nu in conflict; cea mai specifica o descrie corect.
# Fara regula asta, garda de ambiguitate anula 14 din cele 16 valori pe care tocmai
# le adaugasem.
LANT_GEOGRAFIC = ["sepa", "ue", "extern"]        # de la cel mai specific
# ...iar astea se exclud reciproc si intre ele si cu lantul: banii nu pot pleca in
# acelasi timp in tara si in afara ei, nici sa rămana si sa nu rămana in banca.
DESTINATII_EXCLUSIVE = {"national", "intrabancar", "interbancar"}


def _cea_mai_specifica(potriviri):
    """Din mai multe destinatii potrivite: cea mai specifica, sau None daca se bat."""
    if len(potriviri) == 1:
        return next(iter(potriviri))
    if potriviri & DESTINATII_EXCLUSIVE:
        return None                  # exclusivele nu se combina cu nimic
    if potriviri <= set(LANT_GEOGRAFIC):
        return next(d for d in LANT_GEOGRAFIC if d in potriviri)
    return None


def _destinatie(concept, nume, context):
    """Destinatia banilor, cu numele serviciului inaintea contextului.

    Aceeasi regula ca la concept, si a treia data in proiect cand e nevoie de ea:
    dovada locala bate contextul. Verificarea de mana pe 18 atribuiri noi a gasit
    exact aceasta greseala — "Retragere de numerar ATM local" la Salt primea `ue`,
    fiindca secțiunea paginii e "ÎNCASĂRI ȘI PLĂȚI CĂTRE STATE MEMBRE ALE UE". Ce
    spune eticheta despre ea insasi bate ce spune pagina in jurul ei.

    Iar cand eticheta numeste DOUA destinatii care se exclud ("Eliberare de numerar
    în/afara României de la ghișee/ATM-uri BCR sau ale altor bănci"), nu se alege
    niciuna: comisionul se aplica la amandoua, deci nu e nici una, nici alta.
    """
    if concept not in CONCEPTE_CU_DESTINATIE:
        return None
    if RE_AMBELE_DESTINATII.search(nume):
        return None
    din_nume = {n for n, tipar in DESTINATII if re.search(tipar, nume, re.I)}
    if din_nume:
        return _cea_mai_specifica(din_nume)
    if RE_AMBELE_DESTINATII.search(context):
        return None
    din_context = {n for n, tipar in DESTINATII if re.search(tipar, context, re.I)}
    return _cea_mai_specifica(din_context) if din_context else None


def produs_canonic(inregistrare):
    """(produs, segment) pentru o rata de pe web, sau (None, ...) daca nu se mapeaza.

    Se caută in firimitura de navigație, in URL si in textul-sursa. URL-ul e adesea
    cel mai curat dintre cele trei: "/credite/credit-george" nu are titlu de
    marketing in el.
    """
    text = str(inregistrare.get("text_sursa") or "").replace("-", " ")
    pagina = " ".join(str(inregistrare.get(c) or "").replace("-", " ") for c in
                      ("produs", "sursa_url", "categorie"))
    # Textul INAINTEA paginii: valoarea a venit din text, deci textul e dovada
    # locala. Cu pagina prima, o știre despre "un credit pentru mașini electrice",
    # aflata pe pagina Noua Casă a Libra, era raportata drept dobanda la Noua
    # Casă. Textul spune singur despre ce produs vorbește; titlul paginii spune
    # doar pe ce pagina a nimerit.
    produs = _potrivire(PRODUSE, text) or _potrivire(PRODUSE, pagina)
    segment = _potrivire(SEGMENTE_RATE, f"{text} {pagina}")
    if segment is None and inregistrare.get("categorie") == "business":
        segment = "pj"
    return produs, segment
