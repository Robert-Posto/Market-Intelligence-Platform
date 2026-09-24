import datetime
import os
import sys
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import versiuni


def rand(sursa, data, segment="pj"):
    return {"banca": "bcr", "sursa": f"https://cdn.x/{sursa}", "tip_sursa": "document",
            "data_vigoare": data, "segment": segment, "stare_data": "IN_VIGOARE"}


AZI = datetime.date(2026, 9, 24)


class TestVersiuni(unittest.TestCase):
    def test_versiunea_noua_ramane_cea_veche_devine_istoric(self):
        b = [rand("BCR_Tarife-PJ_RO_1-iulie-2026.pdf", "2026-07-01"),
             rand("BCR_Tarife-PJ_RO_1-august-2026.pdf", "2026-08-01")]
        versiuni.marcheaza(b, azi=AZI)
        self.assertEqual([x["stare_data"] for x in b], ["ISTORIC", "IN_VIGOARE"])

    def test_traducerea_e_dublura(self):
        b = [rand("BCR_Tarife-PJ_RO_1-august-2026.pdf", "2026-08-01"),
             rand("BCR_Tarife-PJ_EN_01.08.2026.pdf", "2026-08-01")]
        versiuni.marcheaza(b, azi=AZI)
        self.assertEqual(b[1]["stare_data"], "DUBLURA")
        self.assertEqual(b[0]["stare_data"], "IN_VIGOARE")

    def test_familie_veche_sub_alt_nume_devine_istoric(self):
        b = [rand("BCR_Tarife-PJ_RO_1-august-2026.pdf", "2026-08-01"),
             rand("Tarif-comisioane-persoane-juridice-valabil-23.12.2024.pdf", "2024-12-23")]
        versiuni.marcheaza(b, azi=AZI)
        self.assertEqual(b[1]["stare_data"], "ISTORIC")

    def test_segmente_diferite_nu_se_ating(self):
        b = [rand("Tarife_PJ_2026.pdf", "2026-08-01", "pj"),
             rand("Tarife_PF_2023.pdf", "2023-01-01", "pf")]
        versiuni.marcheaza(b, azi=AZI)
        self.assertEqual([x["stare_data"] for x in b], ["IN_VIGOARE", "IN_VIGOARE"])


if __name__ == "__main__":
    unittest.main()
