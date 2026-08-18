import psycopg
from .db import get_conn_string

CREATE_TICKETS_TABLE = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id BIGSERIAL PRIMARY KEY,
    customer_email TEXT NOT NULL, 
    customer_query TEXT NOT NULL,
    status TEXT DEFAULT 'Open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

def init_tickets_db() -> None:
    with psycopg.connect(get_conn_string()) as conn:
        conn.execute(CREATE_TICKETS_TABLE)