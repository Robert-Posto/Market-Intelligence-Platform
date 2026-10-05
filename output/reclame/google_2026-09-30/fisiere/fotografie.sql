SELECT c.advertiser_id, c.advertiser_disclosed_name, c.advertiser_legal_name, c.advertiser_location,
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
         'AR06821672504419942401', 'AR17818043342127104001',  -- bt
         'AR09420690565374148609', 'AR18305299736816517121',  -- ing
         'AR01664430875242135553',  -- bcr
         'AR05866526753370931201',  -- raiffeisen
         'AR07098428377224183809', 'AR08665437127766441985', 'AR11406278393268797441',  -- revolut
         'AR07634580698245890049',  -- nexent
         'AR16666054893395509249',  -- cec
         'AR10658922043308769281',  -- tbi
         'AR14320414390799564801',  -- salt
         'AR17078268812035358721',  -- libra
         'AR15233555825550163969',  -- unicredit
         'AR00158896541363339265',  -- garanti
         'AR18194238221913686017',  -- patria
         'AR02712531297808416769', 'AR17516865924500553729', 'AR08018363952020848641',  -- bcr filiala
         'AR03431759288471650305'   -- brd filiala
       )
       OR REGEXP_CONTAINS(UPPER(IFNULL(c.ad_funded_by, '')), r'BANCA TRANSILVANIA|BANCA COMERCIAL[AĂ] ROM[AÂ]N[AĂ]|\bBCR\b|\bBRD\b|SOCI[EÉ]T[EÉ] G[EÉ]N[EÉ]RALE|CEC BANK|ING BANK|RAIFFEISEN BANK|UNICREDIT|INTESA SANPAOLO|VISTA BANK|PATRIA BANK|EXIM ?BANK|EXIM BANCA|LIBRA INTERNET|PROCREDIT|\bREVOLUT\b|TBI BANK|GARANTI BANK|GARANTI BBVA|SALT BANK|CITIBANK|BNP PARIBAS|CETELEM|CREDITCOOP|INVESTI[TȚŢ]II [SȘŞ]I DEZVOLTARE|BANK OF CHINA|CREDEX|TECH ?VENTURES BANK|\bBRCI\b|ROM[AÂ]N[AĂ] DE CREDITE|LOCUIN[TȚŢ]E|NEXENT|BANORIENT|\bPKO\b'))
ORDER BY c.advertiser_id, r.last_shown DESC
