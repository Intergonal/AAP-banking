import os

import psycopg
from werkzeug.security import generate_password_hash

from .db import get_conn_string

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    disabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

CREATE_TRADING_ACCOUNTS_TABLE = """
CREATE TABLE IF NOT EXISTS trading_accounts (
    user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    cash NUMERIC(14, 2) NOT NULL DEFAULT 100000.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

CREATE_POSITIONS_TABLE = """
CREATE TABLE IF NOT EXISTS positions (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    avg_price NUMERIC(14, 4) NOT NULL,
    PRIMARY KEY (user_id, ticker)
);
"""

CREATE_TRANSACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity INTEGER NOT NULL,
    price NUMERIC(14, 4) NOT NULL,
    total NUMERIC(14, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_transactions_user
    ON transactions(user_id, created_at DESC);
"""

CREATE_TRANSFERS_TABLE = """
CREATE TABLE IF NOT EXISTS transfers (
    id BIGSERIAL PRIMARY KEY,
    from_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(14, 2) NOT NULL CHECK (amount > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_transfers_from
    ON transfers(from_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transfers_to
    ON transfers(to_user_id, created_at DESC);
"""

ALTER_USERS_TABLE = """
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS disabled BOOLEAN NOT NULL DEFAULT FALSE;
"""

CREATE_PII_REDACTION_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS pii_redaction_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name TEXT,
    original_text TEXT NOT NULL,
    redacted_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pii_redaction_history_user_created
    ON pii_redaction_history(user_id, created_at DESC);
"""

CREATE_SHAREHOLDER_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS shareholder_documents (
    id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_shareholder_documents_path
    ON shareholder_documents(file_path);
"""

CREATE_SHAREHOLDER_DOCUMENT_CHUNKS_TABLE = """
CREATE TABLE IF NOT EXISTS shareholder_document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES shareholder_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding_vector JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(document_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_shareholder_document_chunks_document
    ON shareholder_document_chunks(document_id, chunk_index);
"""


def _seed_admin() -> None:
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not username or not password:
        return
    with psycopg.connect(get_conn_string()) as conn:
        conn.execute(
            """
            INSERT INTO users (email, password_hash, name, is_admin)
            VALUES (%s, %s, 'Administrator', TRUE)
            ON CONFLICT (email) DO UPDATE
            SET password_hash = EXCLUDED.password_hash, is_admin = TRUE
            """,
            (username.strip().lower(), generate_password_hash(password)),
        )


def init_db() -> None:
    with psycopg.connect(get_conn_string()) as conn:
        conn.execute(CREATE_USERS_TABLE)
        conn.execute(ALTER_USERS_TABLE)
        conn.execute(CREATE_TRADING_ACCOUNTS_TABLE)
        conn.execute(CREATE_POSITIONS_TABLE)
        conn.execute(CREATE_TRANSACTIONS_TABLE)
        conn.execute(CREATE_TRANSFERS_TABLE)
        conn.execute(CREATE_PII_REDACTION_HISTORY_TABLE)
        conn.execute(CREATE_SHAREHOLDER_DOCUMENTS_TABLE)
        conn.execute(CREATE_SHAREHOLDER_DOCUMENT_CHUNKS_TABLE)
    _seed_admin()