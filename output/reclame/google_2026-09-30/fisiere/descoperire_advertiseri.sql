-- Descoperirea advertiserilor: toți advertiserii cu reclame livrate în RO al căror
-- nume, nume juridic sau plătitor seamănă cu una dintre cele 30 de bănci din
-- ingest/banks.py. Un rând pe advertiser, deci rezultatul e mic.
-- E reuniunea celor două căutări rulate pe 29.09, cu tiparele strânse după ce au adus
-- falsuri pozitive (151 de firme „Exim”, 28 „BID”, bănci Raiffeisen străine, „Revolution”);
-- în forma asta n-a fost rulată. Rezultatul se clasifică de mână în google_advertiseri.csv.
SELECT c.advertiser_id,
       c.advertiser_disclosed_name,
       c.advertiser_legal_name,
       c.advertiser_location,
       COUNT(*) AS reclame_in_ro,
       MIN(r.first_shown) AS prima_afisare,
       MAX(r.last_shown) AS ultima_afisare
FROM `bigquery-public-data.google_ads_transparency_center.creative_stats` AS c,
     UNNEST(c.region_stats) AS r
WHERE r.region_code = 'RO'
  AND REGEXP_CONTAINS(
        UPPER(CONCAT(IFNULL(c.advertiser_disclosed_name, ''), ' ', IFNULL(c.advertiser_legal_name, ''), ' ',
                     IFNULL(c.ad_funded_by, ''))),
        r'BANCA TRANSILVANIA|BANCA COMERCIAL[AĂ] ROM[AÂ]N[AĂ]|\bBCR\b|\bBRD\b|SOCI[EÉ]T[EÉ] G[EÉ]N[EÉ]RALE|CEC BANK|ING BANK|RAIFFEISEN BANK|UNICREDIT|INTESA SANPAOLO|VISTA BANK|PATRIA BANK|EXIM ?BANK|EXIM BANCA|BANCA DE EXPORT|LIBRA INTERNET|PROCREDIT|\bREVOLUT\b|TBI BANK|GARANTI BANK|GARANTI BBVA|SALT BANK|CITIBANK|BNP PARIBAS|CETELEM|CREDITCOOP|CENTRAL[AĂ] COOPERATIST|INVESTI[TȚŢ]II [SȘŞ]I DEZVOLTARE|BANK OF CHINA|CREDEX|TECH ?VENTURES BANK|\bBRCI\b|ROM[AÂ]N[AĂ] DE CREDITE|LOCUIN[TȚŢ]E|NEXENT|BANORIENT|\bPKO\b')
GROUP BY 1, 2, 3, 4
ORDER BY reclame_in_ro DESC
