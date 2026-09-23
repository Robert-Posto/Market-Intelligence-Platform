"""Cursul de referinta BNR din feedul XML oficial (curs.bnr.ro).

Feedul e publicat explicit pentru consum automatizat, deci nu are nevoie de browser.
"""
import urllib.request
import xml.etree.ElementTree as ET

FEED_ZI = "https://curs.bnr.ro/nbrfxrates.xml"
FEED_10_ZILE = "https://curs.bnr.ro/nbrfxrates10days.xml"
NS = {"b": "https://www.bnr.ro/xsd"}

from . import UA


def curs_referinta(url=FEED_ZI, timeout=30):
    """Returneaza cursurile de referinta BNR: {data, cursuri: {valuta: valoare}}."""
    cerere = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(cerere, timeout=timeout) as r:
        xml = r.read()

    rad = ET.fromstring(xml)
    rezultat = {"sursa": url, "zile": []}

    data_publicare = rad.find(".//b:PublishingDate", NS)
    if data_publicare is not None:
        rezultat["data_publicare"] = data_publicare.text

    for cub in rad.findall(".//b:Cube", NS):
        cursuri = {}
        for rata in cub.findall("b:Rate", NS):
            valuta = rata.get("currency")
            multiplicator = int(rata.get("multiplier", 1))
            try:
                valoare = float(rata.text)
            except (TypeError, ValueError):
                continue
            # normalizam la 1 unitate de valuta
            cursuri[valuta] = round(valoare / multiplicator, 6)
        rezultat["zile"].append({"data": cub.get("date"), "cursuri": cursuri})

    return rezultat
