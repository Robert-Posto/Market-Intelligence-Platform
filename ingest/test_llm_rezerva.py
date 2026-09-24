import json
import os
import sys
import types
import unittest

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.dirname(AICI), AICI]

import llm_rezerva


class ClientFals:
    def __init__(self, valori):
        self.valori = valori
        self.messages = self

    def create(self, **kw):
        text = json.dumps({"valori": self.valori})
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(type="text", text=text)],
            usage=types.SimpleNamespace(input_tokens=100, output_tokens=20))


class TestRezerva(unittest.TestCase):
    LINIE = "Depozit 6 luni\t4,25%\t12 luni\t4,60%"

    def test_accepta_doar_cifre_din_text(self):
        client = ClientFals([
            {"tip_rata": "nominala", "valoare": 4.25, "perioada": "6 luni", "citat": "4,25%"},
            {"tip_rata": "nominala", "valoare": 9.99, "perioada": "24 luni", "citat": "9,99%"},
        ])
        rez = llm_rezerva.extrage([self.LINIE], "libra", "https://x.ro/d", "depozite",
                                  client=client)
        self.assertEqual([b["valoare"] for b in rez], [4.25])
        self.assertLessEqual(rez[0]["incredere"], 0.6)
        self.assertEqual(rez[0]["citat"], self.LINIE)
        self.assertTrue(rez[0]["ambiguu"])          # merge în coada de verificare

    def test_cifra_trebuie_sa_fie_intreaga(self):
        # 4,2 nu e „în text" doar pentru că apare ca început al lui 4,25
        self.assertFalse(llm_rezerva.cifra_in_text(4.2, self.LINIE))
        self.assertTrue(llm_rezerva.cifra_in_text(4.6, self.LINIE))

    def test_fara_linii_fara_apel(self):
        self.assertEqual(llm_rezerva.extrage([], "libra", "u", "depozite", client=None), [])


if __name__ == "__main__":
    unittest.main()
