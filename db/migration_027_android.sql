-- Migrarea 027: aplicațiile Android ale băncilor (analiza statică a APK-urilor).
--
-- Sursa: pachetul lui Nicolae „MIP_android_pentru_Robert_2026-10-05”: 24 de
-- aplicații de la 22 de bănci, 27 de versiuni, analizate din manifest, resurse
-- și lista fișierelor din APK, plus pornirea aplicației pe un telefon de test.
-- Fără Play Store, fără decompilare, fără date de utilizator. Se încarcă cu
-- `ingest/load_android.py` (CSV-urile din `date/` ale pachetului).
--
-- Tabele separate de `app_release` (iOS): la BRD și Nexent două aplicații ale
-- aceleiași bănci pot avea același număr de versiune, iar cheia unică de acolo
-- nu conține `app_id`. Legătura între tabele e `package` (identificatorul
-- aplicației pe Android); banca e în `android_aplicatii.id_banca`.
--
-- `provenienta` pe fiecare rând (ex. `android_static_2026-10-05`): reîncărcarea
-- aceluiași pachet șterge și rescrie doar rândurile lui; alte pachete rămân.
-- Capturile, reconstrucțiile și logo-urile din pachet NU se încarcă aici.
--
-- Idempotentă: se poate rula de mai multe ori.

CREATE TABLE IF NOT EXISTS android_aplicatii (
    id                        BIGSERIAL PRIMARY KEY,
    id_banca                  BIGINT NOT NULL REFERENCES banci(id),
    package                   TEXT NOT NULL UNIQUE,
    aplicatie                 TEXT NOT NULL,
    rol                       TEXT NOT NULL CHECK (rol IN ('principal', 'secundar', 'reper')),
    versiune_analizata        TEXT,
    versiune_cea_mai_noua     TEXT,
    version_code_cea_mai_noua BIGINT,
    framework                 TEXT,
    platforma_tehnica         TEXT,
    captura                   TEXT CHECK (captura IN ('ok', 'negru_text', 'negru_nimic', 'blocat')),
    min_sdk                   INTEGER,
    target_sdk                INTEGER,
    nr_permisiuni             INTEGER,
    nr_texte_in_apk           INTEGER,
    provenienta               TEXT NOT NULL,
    incarcat_la               TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_android_aplicatii_banca ON android_aplicatii (id_banca);
COMMENT ON COLUMN android_aplicatii.captura IS
  'ok = captura merge; negru_text = ecran protejat, textul se citește; negru_nimic = protejat și textul; blocat = aplicația refuză telefonul de test (mod dezvoltator).';
COMMENT ON COLUMN android_aplicatii.versiune_analizata IS
  'Versiunea pe care s-au calculat funcționalitățile, profilul tehnic și textele; poate fi mai veche decât versiune_cea_mai_noua.';

CREATE TABLE IF NOT EXISTS android_versiuni (
    package             TEXT NOT NULL,
    version_name        TEXT NOT NULL,
    version_code        BIGINT,
    min_sdk             INTEGER,
    target_sdk          INTEGER,
    framework           TEXT,
    nr_permisiuni       INTEGER,
    nr_trackere         INTEGER,
    nr_biblioteci       INTEGER,
    nr_librarii_native  INTEGER,
    nr_fisiere_apk      INTEGER,
    sha256_base_apk     TEXT,
    data_extragere      DATE,
    provenienta         TEXT NOT NULL,
    UNIQUE (package, version_name)
);

CREATE TABLE IF NOT EXISTS android_permisiuni (
    package       TEXT NOT NULL,
    version_name  TEXT NOT NULL,
    permisiune    TEXT NOT NULL,
    provenienta   TEXT NOT NULL,
    UNIQUE (package, version_name, permisiune)
);

CREATE TABLE IF NOT EXISTS android_trackere (
    package       TEXT NOT NULL,
    version_name  TEXT NOT NULL,
    tracker       TEXT NOT NULL,
    categorii     TEXT,
    dovada        TEXT,
    provenienta   TEXT NOT NULL,
    UNIQUE (package, version_name, tracker)
);

CREATE TABLE IF NOT EXISTS android_biblioteci (
    package       TEXT NOT NULL,
    version_name  TEXT NOT NULL,
    biblioteca    TEXT NOT NULL,
    versiune      TEXT,
    provenienta   TEXT NOT NULL,
    UNIQUE (package, version_name, biblioteca)
);

CREATE TABLE IF NOT EXISTS android_functionalitati (
    package       TEXT NOT NULL,
    functie       TEXT NOT NULL,
    titlu         TEXT,
    verdict       TEXT NOT NULL CHECK (verdict IN ('sigur', 'probabil', 'absent', 'neconcludent')),
    surse         TEXT,
    dovada_text   TEXT,
    provenienta   TEXT NOT NULL,
    UNIQUE (package, functie)
);
COMMENT ON COLUMN android_functionalitati.verdict IS
  'sigur = găsit în cel puțin 2 surse (cod/text/assets); probabil = într-o sursă; absent; neconcludent = aplicație web cu textul pe server, absența nu dovedește nimic.';

CREATE TABLE IF NOT EXISTS android_portofele (
    package                 TEXT PRIMARY KEY,
    ropay_text              INTEGER,
    googlepay_text          INTEGER,
    applepay_text_ios       INTEGER,
    wearable_text           INTEGER,
    hce_servicii            INTEGER,
    nfc_permisiune          INTEGER,
    gpay_push_provisioning  INTEGER,
    gpay_wallet_api         INTEGER,
    cauta_google_wallet     INTEGER,
    provenienta             TEXT NOT NULL
);
COMMENT ON TABLE android_portofele IS
  'Semnale din APK, NU acceptarea Google/Apple Pay: un card se poate adăuga direct din Google Wallet, fără nimic în aplicația băncii. Sigure: hce_servicii (portofel propriu contactless), gpay_push_provisioning (butonul „Adaugă în Google Wallet”).';

CREATE TABLE IF NOT EXISTS android_profil_tehnic (
    package       TEXT NOT NULL,
    tip           TEXT NOT NULL,
    valoare       TEXT NOT NULL,
    provenienta   TEXT NOT NULL,
    UNIQUE (package, tip, valoare)
);

CREATE TABLE IF NOT EXISTS android_schimbari_versiuni (
    package       TEXT NOT NULL,
    de_la         TEXT NOT NULL,
    la            TEXT NOT NULL,
    camp          TEXT NOT NULL,
    adaugat       TEXT,
    eliminat      TEXT,
    provenienta   TEXT NOT NULL,
    UNIQUE (package, de_la, la, camp)
);

CREATE TABLE IF NOT EXISTS android_texte_ecran (
    id            BIGSERIAL PRIMARY KEY,
    package       TEXT NOT NULL,
    sursa         TEXT NOT NULL,
    data          DATE,
    pas           INTEGER,
    text          TEXT NOT NULL,
    provenienta   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_android_texte_package ON android_texte_ecran (package);

CREATE TABLE IF NOT EXISTS android_note (
    id            BIGSERIAL PRIMARY KEY,
    package       TEXT NOT NULL,
    nota          TEXT NOT NULL,
    provenienta   TEXT NOT NULL
);
