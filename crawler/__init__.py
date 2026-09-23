# Robotul se identifica cu nume si contact, cum cere sectiunea 1 din arhitectura;
# acelasi UA ca ingest/scraper.py, contactul cerut de colegul care il detine.
# Masurat pe 23 sept, pe cele 23 de banci: un UA anonim "compatible; ...Bot" era
# blocat la intrare de salt, tbi si cetelem (149/460 cerinte), iar un UA cu nume
# si contact trece peste tot unde trecea vechiul UA de Chrome (165/460).
UA = ("LibraBank-MarketIntel-Test/0.1 "
      "(test personal, doar date publice; contact: robert.postolache@librabank.ro)")
