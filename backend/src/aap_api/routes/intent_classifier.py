from flask import Blueprint, jsonify, request

intent_classifier = Blueprint(
    "intent_classifier", __name__, url_prefix="/api/intent-classifier"
)


@intent_classifier.get("/health")
def health():
    return jsonify({"status": "ok", "service": "intent-classifier"})


@intent_classifier.post("/classify")
def classify():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    return jsonify({"text": text, "intent": "unknown", "confidence": 0.0})
