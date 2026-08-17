import psycopg

from .db import get_conn_string

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def init_db() -> None:
    with psycopg.connect(get_conn_string()) as conn:
        conn.execute(CREATE_USERS_TABLE)