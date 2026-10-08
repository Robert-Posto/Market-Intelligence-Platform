-- Migrarea 038: tipul de job `aplicatii_mobile` (aplicația unei bănci pe iOS și Android + brief-ul AI al recenziilor).
--
-- DE CE: `jobs.type` are cheie străină spre job_types, iar ingest/actualizeaza_aplicatii.py
-- își scrie rularea ca job (durata, tokenii și costul brief-ului, erorile pe platformă), pornit
-- din terminal sau din „Rulare manuală”. Fără rândul ăsta, jurnalul ar refuza INSERT-ul și
-- jobul ar rula nejurnalizat; estimarea de cost din „Rulare manuală” se ia tot de aici.
--
-- Idempotentă: a doua rulare doar rescrie textele.

INSERT INTO job_types (cod, denumire, descriere, script, ordine) VALUES
    ('aplicatii_mobile', 'Aplicații mobile',
     'Nota, evaluările, descărcările, capturile și recenziile din App Store și Google Play, apoi brief-ul AI al recenziilor. Scrie în app_release / app_review și în date/google_play*.json, date/rezumate_recenzii*.json.',
     'ingest/actualizeaza_aplicatii.py', 40)
ON CONFLICT (cod) DO UPDATE SET
    denumire = EXCLUDED.denumire, descriere = EXCLUDED.descriere,
    script = EXCLUDED.script, ordine = EXCLUDED.ordine;
