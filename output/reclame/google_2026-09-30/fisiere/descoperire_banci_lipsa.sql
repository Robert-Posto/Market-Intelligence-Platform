-- Advertiserii celor 17 bănci din ingest/banks.py negăsite în fotografia din 29.09,
-- căutați sub toate numele lor; un rând pe advertiser, deci rezultatul e mic.
SELECT c.advertiser_id,
       c.advertiser_disclosed_name,
       c.advertiser_legal_name,
       c.advertiser_location,
       COUNT(*) AS reclame_in_ro,
       MAX(r.last_shown) AS ultima_afisare
FROM `bigquery-public-data.google_ads_transparency_center.creative_stats` AS c,
     UNNEST(c.region_stats) AS r
WHERE r.region_code = 'RO'
  AND REGEXP_CONTAINS(
        UPPER(CONCAT(IFNULL(c.advertiser_disclosed_name, ''), ' ', IFNULL(c.advertiser_legal_name, ''))),
        r'\bBRD\b|SOCI[EÉ]T[EÉ] G[EÉ]N[EÉ]RALE|INTESA|VISTA BANK|MARFIN|EXIM|EXPORT[ -]IMPORT|BANCA ROM[AÂ]NEASC|PROCREDIT|CITIBANK|CITIGROUP|\bCITI\b|BNP|CETELEM|CREDITCOOP|COOPERATIST|INVESTI[TȚŢ]II [SȘŞ]I DEZVOLTARE|\bBID\b|BANK OF CHINA|CREDEX|TECH ?VENTURES|\bBRCI\b|ROM[AÂ]N[AĂ] DE CREDITE|LOCUIN[TȚŢ]E|BANORIENT|\bPKO\b|BANK POLSKI')
GROUP BY 1, 2, 3, 4
ORDER BY reclame_in_ro DESC
