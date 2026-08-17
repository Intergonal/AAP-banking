from flask import Blueprint, jsonify

stock_assistant = Blueprint(
    "stock_assistant", __name__, url_prefix="/api/stock-assistant"
)


@stock_assistant.get("/health")
def health():
    return jsonify({"status": "ok", "service": "stock-assistant"})


@stock_assistant.get("/quote/<symbol>")
def quote(symbol):
    return jsonify({"symbol": symbol, "price": 245.31, "currency": "USD"})
