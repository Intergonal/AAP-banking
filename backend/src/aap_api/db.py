import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_conn_string() -> str:
    conn_string = os.getenv("DATABASE_URL")
    if not conn_string:
        raise RuntimeError("DATABASE_URL is not set")
    return conn_string


def check_connection() -> str:
    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            return cur.fetchone()[0]