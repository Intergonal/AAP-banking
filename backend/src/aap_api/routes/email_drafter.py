from flask import Blueprint, jsonify, request

email_drafter = Blueprint(
    "email_drafter", __name__, url_prefix="/api/email-drafter"
)


@email_drafter.get("/health")
def health():
    return jsonify({"status": "ok", "service": "email-drafter"})


@email_drafter.post("/draft")
def draft():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")
    return jsonify({"prompt": prompt, "subject": "", "body": ""})
