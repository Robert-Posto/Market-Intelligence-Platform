-- Migrarea 040: utilizatorii aplicației și rolul lor, date din pagina „Utilizatori”, nu din AD.
--
-- DE CE: AD-ul verifică doar parola; rolurile se dau în aplicație, ca în SCC (decizia din
-- 09.10.2026). Grupurile AD MCC-Admin / MCC-Analist cerute la început nu există și nu se vor crea.
--
-- Cine scrie: app/utilizatori.py, singurul loc din server care scrie în bază.
--   - la prima logare reușită în AD contul apare aici fără rol (blocat), ca adminul să-l vadă;
--     excepție contul din MCC_ADMIN_INITIAL, care primește admin la creare (și doar atunci);
--   - rolul și starea se schimbă din pagina „Utilizatori” (POST /api/utilizatori/modifica, doar admin).
--
-- 039 e lăsată liberă pentru ramura dinu-george, care are încă o migrare 038 nelivrată.
--
-- Idempotent: IF NOT EXISTS.

BEGIN;

CREATE TABLE IF NOT EXISTS utilizatori (
    -- sAMAccountName, cu litere mici (autentificare.normalizeaza_utilizator)
    utilizator    TEXT PRIMARY KEY CHECK (utilizator = lower(utilizator) AND utilizator <> ''),
    -- displayName din AD, actualizat la fiecare logare
    nume          TEXT NOT NULL,
    -- NULL = cont neaprobat: parola e bună, dar aplicația nu-l lasă să intre
    rol           TEXT CHECK (rol IN ('admin', 'analist')),
    activ         BOOLEAN NOT NULL DEFAULT TRUE,
    creat         TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- ultima verificare reușită a parolei în AD, chiar dacă logarea a fost apoi refuzată (fără rol)
    ultima_logare TIMESTAMPTZ,
    modificat     TIMESTAMPTZ,
    modificat_de  TEXT
);

COMMIT;
