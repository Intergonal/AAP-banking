import psycopg
from .db import get_conn_string

# Using email as the primary identifier to link to the users table
CREATE_TICKETS_TABLE = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id BIGSERIAL PRIMARY KEY,
    customer_email TEXT REFERENCES users(email) ON DELETE CASCADE,
    customer_query TEXT NOT NULL,
    intent TEXT,
    sentiment TEXT,
    status TEXT DEFAULT 'Open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

CREATE_DRAFTS_TABLE = """
CREATE TABLE IF NOT EXISTS draft_history (
    draft_id BIGSERIAL PRIMARY KEY,
    ticket_id BIGINT REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    draft_version INT NOT NULL,
    draft_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

def init_tickets_db() -> None:
    with psycopg.connect(get_conn_string()) as conn:
        conn.execute(CREATE_TICKETS_TABLE)
        conn.execute(CREATE_DRAFTS_TABLE)