import psycopg
from flask import Blueprint, jsonify, request
from ..db import get_conn_string

tickets_bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

@tickets_bp.post("/submit")
def submit_ticket():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    query = data.get("query")

    if not email or not query:
        return jsonify({"error": "Email and query are required"}), 400

    try:
        with psycopg.connect(get_conn_string()) as conn:
            result = conn.execute(
                """
                INSERT INTO tickets (customer_email, customer_query) 
                VALUES (%s, %s) 
                RETURNING ticket_id;
                """,
                (email, query)
            ).fetchone()
            
            ticket_id = result[0] if result else None
            conn.commit()

        return jsonify({"status": "success", "ticket_id": ticket_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tickets_bp.get("/open")
def get_open_tickets():
    try:
        with psycopg.connect(get_conn_string()) as conn:
            # Fetching only open tickets, ordering by oldest first
            rows = conn.execute(
                """
                SELECT ticket_id, customer_email, customer_query, created_at 
                FROM tickets 
                WHERE status = 'Open' 
                ORDER BY created_at ASC;
                """
            ).fetchall()

            tickets = [
                {
                    "ticket_id": row[0],
                    "customer_email": row[1],
                    "customer_query": row[2],
                    "created_at": row[3].isoformat()
                }
                for row in rows
            ]

        return jsonify({"tickets": tickets}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tickets_bp.post("/close")
def close_ticket():
    data = request.get_json(silent=True) or {}
    ticket_id = data.get("ticket_id")

    if not ticket_id:
        return jsonify({"error": "ticket_id is required"}), 400

    try:
        with psycopg.connect(get_conn_string()) as conn:
            conn.execute(
                "UPDATE tickets SET status = 'Closed' WHERE ticket_id = %s;",
                (ticket_id,)
            )
            conn.commit()

        return jsonify({"status": "success", "message": f"Ticket {ticket_id} closed."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500