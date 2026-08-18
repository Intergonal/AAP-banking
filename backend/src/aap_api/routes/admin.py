import psycopg
from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash

from ..db import get_conn_string
from .auth import get_current_user

admin = Blueprint("admin", __name__, url_prefix="/api/admin")


def _require_admin():
    user = get_current_user()
    if user is None:
        return None, (jsonify({"error": "unauthorized"}), 401)
    if not user["is_admin"]:
        return None, (jsonify({"error": "forbidden"}), 403)
    return user, None


def _verify_password(user_id, password):
    if not password:
        return False
    with psycopg.connect(get_conn_string()) as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id = %s", (user_id,)
        ).fetchone()
    if row is None:
        return False
    return check_password_hash(row[0], password)


def _confirm_action(user, data):
    """Validate the request and the admin's password for destructive actions."""
    password = data.get("password")
    if not isinstance(password, str) or not password:
        return None, (jsonify({"error": "password is required"}), 400)
    if not _verify_password(user["id"], password):
        return None, (jsonify({"error": "invalid password"}), 401)
    return True, None


@admin.get("/users")
def list_users():
    _, err = _require_admin()
    if err:
        return err

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, is_admin, disabled, created_at "
                "FROM users ORDER BY created_at DESC, id DESC"
            )
            rows = cur.fetchall()

    return jsonify(
        [
            {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "is_admin": row[3],
                "disabled": row[4],
                "created_at": row[5].isoformat(),
            }
            for row in rows
        ]
    )


@admin.patch("/users/<int:user_id>")
def set_user_disabled(user_id):
    user, err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("disabled"), bool):
        return jsonify({"error": "disabled must be a boolean"}), 400
    if data["disabled"] and user_id == user["id"]:
        return jsonify({"error": "you cannot disable your own account"}), 400
    if data["disabled"]:
        ok, err = _confirm_action(user, data)
        if not ok:
            return err

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET disabled = %s WHERE id = %s "
                "RETURNING id, name, email, is_admin, disabled",
                (data["disabled"], user_id),
            )
            row = cur.fetchone()

    if row is None:
        return jsonify({"error": "user not found"}), 404

    return jsonify(
        {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "is_admin": row[3],
            "disabled": row[4],
        }
    )


@admin.delete("/users/<int:user_id>")
def delete_user(user_id):
    user, err = _require_admin()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    ok, err = _confirm_action(user, data)
    if not ok:
        return err
    if user_id == user["id"]:
        return jsonify({"error": "you cannot delete your own account"}), 400

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, email, is_admin, disabled FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return jsonify({"error": "user not found"}), 404
            if row[3]:
                return jsonify({"error": "you cannot delete admin accounts"}), 400
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))

    return jsonify({"id": row[0], "name": row[1], "email": row[2], "deleted": True})