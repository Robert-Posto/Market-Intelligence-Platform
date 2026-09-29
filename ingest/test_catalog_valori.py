"""Teste pentru extracția prețurilor din catalogul intern Libra
(ingest/catalog_libra_valori.py). Fără bază de date.

Fragmentele sunt copiate exact din „Catalog produse 2026-09-28.xlsx"
(coloana „Caracteristicile produsului"), în afară de cel marcat SINTETIC.
"""

import os
import re
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import catalog_libra_valori as C
import normalizeaza as N

FISIER = "Catalog produse 2026-09-28.xlsx"

# cod -> (denumire, categorie_cod, segment, caracteristici) — rânduri reale
REALE = {
    "ABONAMENT_ELITE": ("Abonament ELITE (corporate)", "CONT_CURENT", "PJ",
        "Abonament corporate 225 lei/lună: 50 plăți/încasări lei/euro, 50 SEPA, "
        "50 instrumente de debit, 3 carduri, include Live FX."),
    "ABONAMENT_PFA": ("Abonament PFA", "CONT_CURENT", "PJ",
        "Abonament 29 lei/lună pentru PFA/profesii: cont, card business, IB/MB gratuite, "
        "50 de operațiuni/lună incluse."),
    "ABONAMENT_RISE": ("Abonament RISE", "CONT_CURENT", "PJ",
        "Abonament operațional 50 lei/lună: plăți/încasări nelimitate în lei prin IB/MB, "
        "până la 2 carduri business, retrageri gratuite, mPOS 0,59%."),
    "CONT_ECONOMII": ("Cont de economii", "DEPOZITE", "PF+PJ",
        "Cont de economii în lei cu dobândă la sold zilnic: ~3,00% p.a. la 6-12 luni, "
        "2,50% la 3-6 luni, 2,00% nelimitat cu retrageri oricând."),
    "DEPOZIT_BLITZ_7L": ("Depozit promoțional Blitz (7 luni)", "DEPOZITE", "PF+PJ",
        "Depozit promoțional pe 7 luni, dobândă ~6,25% p.a."),
    "DEPOZIT_1AN_1LUNA": ("Depozit promoțional „1 An și 1 Lună\"", "DEPOZITE", "PF+PJ",
        "Depozit promoțional 13 luni, dobândă totală ~6,60%/6,10% p.a."),
    "CARD_DEBIT_GOLD": ("Card de debit Gold", "CONT_CURENT", "PF+PJ",
        "Card debit cu asigurare de călătorie, cashback, lounge, 3 retrageri gratuite/lună, "
        "1% dobândă la sold peste 500 lei; 48 lei/an."),
    "CARD_DEBIT_FREE": ("Card de debit Free", "CONT_CURENT", "PF+PJ",
        "Card debit fără costuri de emitere sau administrare, cu cashback la parteneri."),
    "LEASING_FINANCIAR": ("Leasing financiar (Libra Development IFN)", "CREDIT_INVESTITII", "PJ",
        "Leasing auto (până la 7 ani, avans de la 15%) și echipamente/utilaje (până la 5 ani, "
        "avans de la 20%), prin IFN-ul grupului."),
    "CREDIT_BERD_PJ": ("Credit de investiții InvestEU BERD", "CREDIT_INVESTITII", "PJ",
        "Credit de investiții cu garanție BERD 80%: până la 10 mil. lei, 12–120 luni, "
        "max. 85% din investiție, grație până la 12 luni."),
    "OVERDRAFT_PF": ("Overdraft (descoperit de cont)", "CREDIT_CAPITAL_LUCRU", "PF",
        "Descoperit autorizat până la 6 salarii nete (max. 70.000 lei), dobândă doar pe suma utilizată."),
}


def produs(cod, **peste):
    denumire, cat, seg, text = REALE[cod]
    p = {"cod": cod, "denumire": denumire, "categorie": None, "categorie_cod": cat,
         "segment": seg, "caracteristici": text, "fisier": FISIER, "foaie": "Catalog produse",
         "rand": 2}
    p.update(peste)
    return p


def extrage(cod, **peste):
    return C.extrage(produs(cod, **peste))


def normalizate(valori):
    return [N.normalizeaza(v) for v in valori]


class TestAbonament(unittest.TestCase):
    def test_abonament_corporate_pe_administrare_cont(self):
        v, _ = extrage("ABONAMENT_ELITE")
        self.assertEqual(len(v), 1)
        r = normalizate(v)[0]
        self.assertEqual((r["camp"], r["valoare_num"], r["unitate"], r["frecventa"]),
                         ("administrare_cont", 225.0, "lei", "lunar"))
        self.assertEqual(r["cod_scenariu"], "comision|pj")
        self.assertEqual(r["citat"], "Abonament corporate 225 lei/lună")
        self.assertEqual(r["serviciu"], "Abonament ELITE (corporate)")
        self.assertEqual((r["tip_sursa"], r["format"], r["rol_sursa"], r["sursa"]),
                         ("document", "xlsx", "conditii", FISIER))

    def test_abonament_fara_adjectiv(self):
        v, n = extrage("ABONAMENT_PFA")
        self.assertEqual([(x["concept"], x["valoare"], x["citat"]) for x in v],
                         [("administrare_cont", 29.0, "Abonament 29 lei/lună")])
        # „IB/MB gratuite" nu devine 0 lei: nu e o sumă scrisă
        self.assertIn("IB/MB gratuite", [x["fragment"] for x in n])

    def test_mpos_ramane_nemapat(self):
        v, n = extrage("ABONAMENT_RISE")
        self.assertEqual([x["valoare"] for x in v], [50.0])
        mpos = [x for x in n if x["fragment"] == "0,59%"]
        self.assertEqual(len(mpos), 1)
        self.assertIn("mPOS", mpos[0]["motiv"])

    def test_abonament_la_produs_care_nu_e_de_cont(self):
        v, n = extrage("ABONAMENT_ELITE", categorie_cod="CARDURI_ACQUIRING")
        self.assertEqual(v, [])
        self.assertIn("nu e de cont", n[0]["motiv"])


class TestDobanziDepozit(unittest.TestCase):
    def test_lista_de_dobanzi_cu_termene(self):
        v, n = extrage("CONT_ECONOMII")
        r = normalizate(v)
        self.assertEqual([(x["camp"], x["valoare_num"], x["frecventa"]) for x in r],
                         [("nominala", 3.0, "6-12 luni"), ("nominala", 2.5, "3-6 luni"),
                          ("nominala", 2.0, "nelimitat")])
        self.assertTrue(all(x["cod_scenariu"] == "depozite|pf|pj" for x in r))
        self.assertTrue(all(x["unitate"] == "procent" for x in r))
        self.assertEqual(r[0]["citat"], "dobândă la sold zilnic: ~3,00% p.a. la 6-12 luni")
        self.assertIn("aproximativ", r[0]["detaliu"])
        self.assertIsNone(r[1]["detaliu"])
        self.assertEqual(n, [])

    def test_termenul_produsului(self):
        v, _ = extrage("DEPOZIT_BLITZ_7L")
        self.assertEqual([(x["valoare"], x["frecventa"], x["citat"]) for x in v],
                         [(6.25, "7 luni", "dobândă ~6,25% p.a.")])

    def test_doua_dobanzi_fara_varianta_nu_se_mapeaza(self):
        v, n = extrage("DEPOZIT_1AN_1LUNA")
        self.assertEqual(v, [])
        self.assertEqual(len(n), 1)
        self.assertEqual(n[0]["fragment"], "dobândă totală ~6,60%/6,10% p.a.")


class TestAmbiguu(unittest.TestCase):
    def test_card_gold_nimic_mapat(self):
        # 1% e dobândă la sold, dar în bază stă lângă dobânda cardului de credit
        # (conturi_carduri); 48 lei/an nu spune ce comision e
        v, n = extrage("CARD_DEBIT_GOLD")
        self.assertEqual(v, [])
        motive = {x["fragment"]: x["motiv"] for x in n}
        self.assertIn("dobândă la sold", motive["1%"])
        self.assertIn("anuală", motive["48 lei"])
        self.assertIn("limită", motive["500 lei"])

    def test_gratuit_nu_devine_zero(self):
        v, n = extrage("CARD_DEBIT_FREE")
        self.assertEqual(v, [])
        self.assertIn("gratuitate", n[0]["motiv"])

    def test_de_la_x_procent_la_credit_fara_dobanda_nu_se_mapeaza(self):
        v, n = extrage("LEASING_FINANCIAR")
        self.assertEqual(v, [])
        self.assertEqual([(x["fragment"], x["motiv"]) for x in n],
                         [("15%", "avans minim, nu dobândă"), ("20%", "avans minim, nu dobândă")])

    def test_procente_de_garantare_si_plafoane(self):
        v, n = extrage("CREDIT_BERD_PJ")
        self.assertEqual(v, [])
        motive = {x["fragment"]: x["motiv"] for x in n}
        self.assertIn("garantare", motive["80%"])
        self.assertIn("limită", motive["85%"])
        self.assertIn("10 mil. lei", motive)

    def test_dobanda_fara_cifra_la_credit(self):
        v, n = extrage("OVERDRAFT_PF")
        self.assertEqual(v, [])
        self.assertEqual([x["fragment"] for x in n], ["70.000 lei"])

    def test_credit_cu_dobanda_si_dae_numite(self):
        # SINTETIC: niciun rând din exportul din 28.09 nu are dobândă de credit;
        # regula e pentru exporturile următoare
        text = "Credit de investiții, dobândă de la 7,50% p.a.; DAE 8,10%."
        v, _ = extrage("CREDIT_BERD_PJ", caracteristici=text)
        r = normalizate(v)
        self.assertEqual([(x["camp"], x["valoare_num"], x["cod_scenariu"]) for x in r],
                         [("nominala", 7.5, "credite|pj"), ("dae", 8.1, "credite|pj")])
        self.assertIn("minimă", r[0]["detaliu"])


class TestCitate(unittest.TestCase):
    def test_citatul_e_textul_exact(self):
        for cod in REALE:
            v, n = extrage(cod)
            text = REALE[cod][3]
            for x in v:
                self.assertIn(x["citat"], text, cod)
            for x in n:
                self.assertIn(x["fragment"], text, cod)


class TestLegaturi(unittest.TestCase):
    def test_transportul_catalogului(self):
        self.assertEqual(N.TRANSPORT[C.METODA], "manual")

    def test_vederea_si_banci_cu_catalog_au_aceeasi_lista(self):
        # vederea nu poate citi Python-ul: lista de bănci stă în SQL separat
        radacina = os.path.dirname(AICI)
        for nume in ("sincronizeaza_vederi.sql", "migration_022_catalog_inlocuieste.sql"):
            with open(os.path.join(radacina, "db", nume), encoding="utf-8") as f:
                sql = f.read()
            m = re.search(r"b\.slug IN \(([^)]*)\)\s*-- BANCI_CU_CATALOG", sql)
            self.assertIsNotNone(m, nume)
            self.assertEqual(set(re.findall(r"'([^']+)'", m.group(1))),
                             set(N.BANCI_CU_CATALOG), nume)


if __name__ == "__main__":
    unittest.main()
