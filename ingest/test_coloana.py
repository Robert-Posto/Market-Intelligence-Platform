import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import extractoare
import normalizeaza as N


def rand(**kw):
    baza = dict(banca="bcr", camp="emitere_card", cod_scenariu=None, serviciu="Emitere card",
                valoare_num=0, valoare_text=None, unitate="lei", conditie=None,
                frecventa=None, data_vigoare=None, citat="0 lei")
    baza.update(kw)
    return baza


class TestColoana(unittest.TestCase):
    def test_segment_din_nume(self):
        self.assertEqual(extractoare.segment_din_nume("Tarife_si_Comisioane_PJ.pdf"), "pj")
        self.assertEqual(extractoare.segment_din_nume("lista-tarife-persoane-fizice.pdf"), "pf")
        self.assertIsNone(extractoare.segment_din_nume("document.pdf"))

    def test_coloane_diferite_nu_se_unesc(self):
        rez = N.dedup([rand(coloana="Visa Classic"), rand(coloana="Mastercard Gold")])
        self.assertEqual(len(rez), 2)

    def test_aceeasi_coloana_se_uneste(self):
        rez = N.dedup([rand(coloana="Visa"), rand(coloana="Visa")])
        self.assertEqual(len(rez), 1)
        self.assertEqual(rez[0]["nr_aparitii"], 2)

    def test_coloana_ajunge_in_randul_normalizat(self):
        b = N.brut(banca="bcr", sursa="https://x.ro/t.pdf", concept="emitere_card", tip="comision_suma",
                   valoare=0, moneda="LEI", serviciu="Emitere card", coloana="Visa Gold",
                   produs="comisioane")
        self.assertEqual(N.normalizeaza(b)["coloana"], "Visa Gold")
        self.assertEqual(N.COLOANE[-1], "coloana")

    def test_documente_fara_tarife_dupa_nume(self):
        self.assertIsNotNone(extractoare.document_fara_tarife(
            "x", "https://x.ro/RAP_cerinte-transparenta-si-publicare_REG_575_pt-2024.pdf"))
        self.assertIsNotNone(extractoare.document_fara_tarife("x", "https://x.ro/Info-Economice-30-04-2025.pdf"))
        self.assertIsNone(extractoare.document_fara_tarife("x", "https://x.ro/Tarife_si_Comisioane_PF.pdf"))
        self.assertIsNone(extractoare.document_fara_tarife("x", "https://x.ro/Ghid_tarife_comisioane.pdf"))


if __name__ == "__main__":
    unittest.main()
