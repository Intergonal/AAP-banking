import os
from datetime import datetime, timedelta, timezone

import jwt
import psycopg
from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_conn_string

auth = Blueprint("auth", __name__, url_prefix="/api/auth")

JWT_ALGORITHM = "HS256"
TOKEN_TTL = timedelta(hours=24)


def _secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    return secret


@auth.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400

    password_hash = generate_password_hash(password)
    try:
        with psycopg.connect(get_conn_string()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id, name, email",
                    (name, email, password_hash),
                )
                row = cur.fetchone()
    except psycopg.errors.UniqueViolation:
        return jsonify({"error": "email already registered"}), 409

    return jsonify({"id": row[0], "name": row[1], "email": row[2]}), 201


@auth.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, password_hash FROM users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()

    if row is None or not check_password_hash(row[3], password):
        return jsonify({"error": "invalid email or password"}), 401

    user_id, name, user_email, _ = row
    token = jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + TOKEN_TTL,
        },
        _secret(),
        algorithm=JWT_ALGORITHM,
    )
    return jsonify(
        {"token": token, "user": {"id": user_id, "name": name, "email": user_email}}
    )


def get_current_user():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    token = header.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email FROM users WHERE id = %s",
                (int(payload["sub"]),),
            )
            row = cur.fetchone()

    if row is None:
        return None
    return {"id": row[0], "name": row[1], "email": row[2]}


@auth.get("/me")
def me():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    return jsonify(user)