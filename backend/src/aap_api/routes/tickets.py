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
    
@tickets_bp.post("/save-draft")
def save_draft():
    data = request.get_json(silent=True) or {}
    ticket_id = data.get("ticket_id")
    draft_text = data.get("draft_text")
    
    # Extract the new metadata
    intent = data.get("intent")
    sentiment = data.get("sentiment")
    confidence = data.get("confidence")

    if not ticket_id or not draft_text:
        return jsonify({"error": "ticket_id and draft_text are required"}), 400

    try:
        with psycopg.connect(get_conn_string()) as conn:
            # Update the ticket metadata if it exists
            if intent and sentiment:
                conn.execute(
                    "UPDATE tickets SET intent = %s, sentiment = %s, confidence = %s WHERE ticket_id = %s;",
                    (intent, sentiment, confidence, ticket_id)
                )
            
            # Save the draft iteration
            conn.execute(
                """
                INSERT INTO draft_history (ticket_id, draft_version, draft_text) 
                VALUES (
                    %s, 
                    (SELECT COALESCE(MAX(draft_version), 0) + 1 FROM draft_history WHERE ticket_id = %s), 
                    %s
                );
                """,
                (ticket_id, ticket_id, draft_text)
            )
            conn.commit()

        return jsonify({"status": "success"}), 201
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
    
@tickets_bp.get("/<int:ticket_id>/workspace")
def get_workspace(ticket_id):
    try:
        with psycopg.connect(get_conn_string()) as conn:
            # Get the metadata from the ticket
            ticket = conn.execute(
                "SELECT intent, sentiment, confidence FROM tickets WHERE ticket_id = %s;", 
                (ticket_id,)
            ).fetchone()
            
            # Get only the most recent draft
            draft = conn.execute(
                "SELECT draft_text FROM draft_history WHERE ticket_id = %s ORDER BY draft_version DESC LIMIT 1;", 
                (ticket_id,)
            ).fetchone()

        if not ticket:
            return jsonify({"error": "Ticket not found"}), 404

        # Return structured data for the React state
        return jsonify({
            "analysis": {
                "intent": ticket[0],
                "sentiment": ticket[1],
                "confidence": float(ticket[2]) if ticket[2] else None
            } if ticket[0] else None,
            "latest_draft": draft[0] if draft else ""
        }), 200
        
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