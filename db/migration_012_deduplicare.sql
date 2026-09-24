-- Migrarea 012: câte celule identice stau în spatele unui rând.
--
-- Problema, măsurată pe extracția din PDF: 3.263 din 15.111 rânduri (21,6%)
-- sunt duplicate exacte — aceeași bancă, același serviciu, aceeași valoare,
-- aceeași pagină. În interfață arătau ca opt rânduri „0 lei" unul sub altul,
-- fără nimic care să le deosebească.
--
-- Cauza nu e o eroare de citire. Tabelele de tarife au o coloană per variantă
-- de produs (Visa Business / Mastercard / Gold), iar parserul citește fiecare
-- celulă ca rând separat. Antetul coloanei se pierde, deci cele cinci rânduri
-- „Emitere card — 0 lei" sunt de fapt cinci tipuri de card care costă toate 0.
--
-- Informația „cinci variante, toate 0 lei" e utilă. Cinci rânduri identice nu
-- sunt. Se păstrează un rând și se numără câte celule l-au produs.
--
-- Nu se șterge nimic retroactiv aici: coloana se adaugă, iar deduplicarea se
-- face la reîncărcare, în `normalizeaza.scrie()`. Așa regula stă în cod, unde
-- se poate citi, nu într-un DELETE rulat o dată și uitat.

ALTER TABLE observations ADD COLUMN IF NOT EXISTS nr_aparitii INTEGER NOT NULL DEFAULT 1;

COMMENT ON COLUMN observations.nr_aparitii IS
  'Câte celule identice din document au produs acest rând. >1 înseamnă de '
  'regulă un tabel cu o coloană per variantă de produs, al cărui antet s-a '
  'pierdut la extracție.';
