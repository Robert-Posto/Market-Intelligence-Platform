"""Scrie interogarea BigQuery pentru o fotografie Google Ads Transparency, din
lista de ID-uri din google_advertiseri.csv, ca lista să stea într-un singur loc.

    python output/reclame/interogare_fotografie.py > output/reclame/fotografie.sql
"""
import collections
import csv
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8")
# Agențiile nu intră pe ID: contul unei agenții aduce și reclamele altor clienți
# (Sense8 a adus 364 de reclame pe 30.09, toate cu plătitor gol). Reclamele unei
# bănci publicate de o agenție vin prin căutarea după plătitor, de mai jos.
ROLURI = ("banca", "filiala")

# `ad_funded_by` e completat doar când plătitorul diferă de advertiser. Căutăm în
# el numele băncilor: Intesa Sanpaolo Bank publică prin WPP Media Romania și a
# apărut doar așa (42 de reclame, 30.09). Tiparul e strâns după prima rulare, unde
# „RAIFFEISEN”, „GARANTI”, „REVOLUT” și „TECH VENTURES” au adus 16 advertiseri străini
# fără legătură (Raiffeisenbanken germane, „Garantie”, „Revolution”).
PLATITORI = (
    r"BANCA TRANSILVANIA|BANCA COMERCIAL[AĂ] ROM[AÂ]N[AĂ]|\bBCR\b|\bBRD\b|SOCI[EÉ]T[EÉ] G[EÉ]N[EÉ]RALE|"
    r"CEC BANK|ING BANK|RAIFFEISEN BANK|UNICREDIT|INTESA SANPAOLO|VISTA BANK|PATRIA BANK|EXIM ?BANK|EXIM BANCA|"
    r"LIBRA INTERNET|PROCREDIT|\bREVOLUT\b|TBI BANK|GARANTI BANK|GARANTI BBVA|SALT BANK|CITIBANK|BNP PARIBAS|"
    r"CETELEM|CREDITCOOP|INVESTI[TȚŢ]II [SȘŞ]I DEZVOLTARE|BANK OF CHINA|CREDEX|TECH ?VENTURES BANK|\bBRCI\b|"
    r"ROM[AÂ]N[AĂ] DE CREDITE|LOCUIN[TȚŢ]E|NEXENT|BANORIENT|\bPKO\b"
)

# Toate câmpurile tabelului, la cererea lui Nicolae (30.09). Estimarea pe datele din
# 29.09 dă 7,6–12 MB în CSV, deci poate trece de limita de 10 MB a descărcării
# locale; peste ea, rezultatul se salvează în Google Drive (până la 1 GB).
# Structurile devin text, fiindcă un CSV nu poate ține liste: `platforme` e
# „SEARCH:1000-2000:<data publicării>;YOUTUBE:…”, iar țintirea e JSON, ale cărei
# câmpuri nu le-am văzut încă.
SQL = """SELECT c.advertiser_id, c.advertiser_disclosed_name, c.advertiser_legal_name, c.advertiser_location,
       c.advertiser_verification_status, c.ad_funded_by, c.is_funded_by_google_ad_grants,
       c.creative_id, c.creative_page_url, c.ad_format_type, c.topic,
       r.region_code, r.first_shown, r.last_shown,
       r.times_shown_lower_bound, r.times_shown_upper_bound,
       r.times_shown_start_date, r.times_shown_end_date, r.times_shown_availability_date,
       ARRAY_LENGTH(c.region_stats) AS nr_tari,
       (SELECT STRING_AGG(CONCAT(s.surface, ':', IFNULL(CAST(s.times_shown_lower_bound AS STRING), ''), '-',
                                 IFNULL(CAST(s.times_shown_upper_bound AS STRING), ''), ':',
                                 IFNULL(s.times_shown_availability_date, '')), ';' ORDER BY s.surface)
        FROM UNNEST(r.surface_serving_stats.surface_serving_stats) AS s) AS platforme,
       TO_JSON_STRING(c.audience_selection_approach_info) AS tintire
FROM `bigquery-public-data.google_ads_transparency_center.creative_stats` AS c,
     UNNEST(c.region_stats) AS r
WHERE r.region_code = 'RO'
  AND (c.advertiser_id IN (
{ids}
       )
       OR REGEXP_CONTAINS(UPPER(IFNULL(c.ad_funded_by, '')), r'{platitori}'))
ORDER BY c.advertiser_id, r.last_shown DESC"""


def main():
    with open(os.path.join(AICI, "google_advertiseri.csv"), encoding="utf-8") as f:
        randuri = [r for r in csv.DictReader(f) if r["rol"] in ROLURI]
    pe_banca = collections.defaultdict(list)
    for r in randuri:
        pe_banca[(r["banca"], r["rol"])].append(r["advertiser_id"])
    linii = []
    for (banca, rol), ids in pe_banca.items():
        eticheta = banca if rol == "banca" else f"{banca} {rol}"
        linii.append("         " + ", ".join(f"'{i}'" for i in ids) + ",  -- " + eticheta)
    linii[-1] = linii[-1].replace(",  --", "   --")
    print(SQL.replace("{ids}", "\n".join(linii)).replace("{platitori}", PLATITORI))


if __name__ == "__main__":
    main()
