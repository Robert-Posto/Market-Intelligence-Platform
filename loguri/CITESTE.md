# Loguri

Rularea de populare inițială din 23 septembrie 2026 scrie în directorul
temporar al sesiunii Claude care a lansat-o:

    %LOCALAPPDATA%\Temp\claude\c--Users-robert-postolache-Desktop-Scraping\
      c386605a-aff1-48ac-993a-266a4af547f2\scratchpad\populare_final.log

Ieșirea e tamponată: fișierul rămâne la 0 octeți până când procesul termină,
apoi se scrie tot dintr-odată. Un fișier de 0 octeți NU înseamnă că rularea a
eșuat.

Directorul acela e al sesiunii și se poate curăța. Dacă log-ul nu mai există,
starea reală se citește direct din bază — care e sursa de adevăr oricum:

    docker exec -i mip-db psql -U mip -d mip -c "
      SELECT metoda_extractie, count(*) AS obs,
             count(data_vigoare) AS cu_data,
             count(*) FILTER (WHERE ambiguu) AS ambigue
      FROM observations GROUP BY 1;"

Ce ar trebui să vezi după o populare reușită:
  - o singură proveniență: `populare`
  - ~50% din rânduri cu `data_vigoare` completată
  - `bronze/` cu câteva sute de fișiere (octeții bruți, păstrați între rulări)

Dacă baza e la 0 observații și niciun proces python nu mai rulează, rularea a
picat: repornește cu

    python ingest/populare_initiala.py --fara-llm
