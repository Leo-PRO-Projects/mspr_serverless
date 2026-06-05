-- Schéma de la base COFRAP — table unique `users`
-- Conforme à l'exemple du sujet : id | username | password | mfa | gendate | expired
-- password et mfa sont stockés CHIFFRÉS (Fernet) — jamais en clair.

CREATE TABLE IF NOT EXISTS users (
    id        SERIAL PRIMARY KEY,
    username  VARCHAR(128) NOT NULL UNIQUE,
    password  TEXT,                       -- mot de passe chiffré (Fernet)
    mfa       TEXT,                       -- secret TOTP chiffré (Fernet)
    gendate   BIGINT,                     -- timestamp Unix de dernière génération
    expired   SMALLINT NOT NULL DEFAULT 0 -- 0 = actif, 1 = expiré
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
