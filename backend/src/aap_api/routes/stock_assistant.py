import psycopg
import yfinance as yf
from decimal import Decimal
from flask import Blueprint, jsonify, request
from google.genai import types

from ..db import get_conn_string
from ..stock_assistant.agent.rag import knowledge_base as kb
from ..stock_assistant.agent.engine import run_agent
from ..stock_assistant.ml import hub_model
from ..stock_assistant.ml.preprocess import TICKERS, build_sequence, fetch_5m_bars
from ..stock_assistant.trading import (
    execute_trade,
    find_recipient,
    get_account,
    get_price,
    reset_account,
    transfer_cash,
)
from .auth import get_current_user

stock_assistant = Blueprint(
    "stock_assistant", __name__, url_prefix="/api/stock-assistant"
)

MODEL_TICKERS = TICKERS


@stock_assistant.get("/health")
def health():
    return jsonify({"status": "ok", "service": "stock-assistant"})


def _serialize_history(history):
    contents = []
    for msg in history or []:
        role = msg.get("role")
        text = msg.get("text") or msg.get("content") or ""
        if role not in ("user", "model") or not text:
            continue
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=text)])
        )
    return contents


@stock_assistant.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    history = _serialize_history(data.get("history") or [])
    user = get_current_user()
    try:
        reply, tool_calls = run_agent(history, message, user_id=user["id"] if user else None)
    except Exception as e:
        return jsonify({"error": f"agent error: {e}"}), 502

    return jsonify({"reply": reply, "tool_calls": tool_calls})


@stock_assistant.get("/quote/<symbol>")
def quote(symbol):
    symbol = symbol.upper()
    try:
        t = yf.Ticker(symbol)
        info = t.fast_info
        price = info.get("last_price") or info.get("lastPrice")
        prev_close = info.get("previous_close")
        currency = info.get("currency") or "USD"
        if price is None:
            return jsonify({"error": f"no price data for {symbol}"}), 404
        change = price - prev_close if prev_close else None
        change_pct = (change / prev_close * 100) if (change is not None and prev_close) else None
        return jsonify({
            "symbol": symbol,
            "price": round(float(price), 2),
            "change": round(float(change), 2) if change is not None else None,
            "change_pct": round(float(change_pct), 2) if change_pct is not None else None,
            "currency": currency,
        })
    except Exception as e:
        return jsonify({"error": f"could not fetch quote for {symbol}: {e}"}), 502


@stock_assistant.post("/predict")
def predict():
    data = request.get_json(silent=True) or {}
    ticker = (data.get("ticker") or "").upper()
    if ticker not in MODEL_TICKERS:
        return jsonify({
            "error": f"ticker must be one of {', '.join(MODEL_TICKERS)}"
        }), 400

    try:
        bars = fetch_5m_bars(ticker)
    except Exception as e:
        return jsonify({"error": f"could not fetch market data for {ticker}: {e}"}), 502

    if bars.empty:
        return jsonify({"error": f"no market data available for {ticker}"}), 502

    try:
        sequence = build_sequence(bars, ticker)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    try:
        result = hub_model.predict(sequence)
        probabilities = result.get("probabilities") or []
        if not probabilities:
            return jsonify({"error": "model returned no probabilities"}), 502
        probability = float(probabilities[0])
    except hub_model.ModelUnavailableError as e:
        return jsonify({"error": str(e)}), 503

    direction = "UP" if probability > 0.5 else "DOWN"
    confidence = probability if direction == "UP" else 1.0 - probability

    return jsonify({
        "ticker": ticker,
        "price": round(float(bars["close"].iloc[-1]), 2),
        "datetime": bars["datetime"].iloc[-1].isoformat(),
        "direction": direction,
        "probability": round(probability, 4),
        "confidence": round(confidence, 4),
    })


# ── Mock trading ──────────────────────────────────────────────────────

PRICE_PERIODS = {
    "1m": ("7d", "1m"),
    "5m": ("60d", "5m"),
    "30m": ("60d", "30m"),
    "1h": ("730d", "1h"),
    "1d": ("10y", "1d"),
}


def _auth_user():
    user = get_current_user()
    if user is None:
        return None
    return user


def _admin_user():
    user = get_current_user()
    if user is None:
        return None
    if not user["is_admin"]:
        return None
    return user


def _live_account(user_id):
    """Enrich the account with live prices and unrealized P&L."""
    account = get_account(user_id)
    total_value = Decimal(str(account["cash"]))
    positions = []
    for pos in account["positions"]:
        try:
            price = get_price(pos["ticker"])
            value = Decimal(str(price)) * pos["quantity"]
            cost = Decimal(str(pos["avg_price"])) * pos["quantity"]
            pl = value - cost
            pl_pct = (pl / cost * 100) if cost else Decimal("0")
        except ValueError:
            price = None
            value = cost = pl = pl_pct = None
        positions.append({
            "ticker": pos["ticker"],
            "quantity": pos["quantity"],
            "avg_price": pos["avg_price"],
            "current_price": float(price) if price is not None else None,
            "market_value": round(float(value), 2) if value is not None else None,
            "unrealized_pl": round(float(pl), 2) if pl is not None else None,
            "unrealized_pl_pct": round(float(pl_pct), 2) if pl_pct is not None else None,
        })
        if value is not None:
            total_value += value
    return {
        **account,
        "positions": positions,
        "total_value": round(float(total_value), 2),
    }


@stock_assistant.get("/account")
def account():
    user = _auth_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    try:
        return jsonify(_live_account(user["id"]))
    except Exception as e:
        return jsonify({"error": f"could not load account: {e}"}), 503


@stock_assistant.post("/trade")
def trade():
    user = _auth_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    try:
        execute_trade(user["id"], data.get("symbol"), data.get("side"), data.get("quantity"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"trade failed: {e}"}), 503
    try:
        return jsonify(_live_account(user["id"]))
    except Exception as e:
        return jsonify({"error": f"trade executed but account load failed: {e}"}), 503


@stock_assistant.post("/account/reset")
def account_reset():
    user = _auth_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    try:
        reset_account(user["id"])
        return jsonify(_live_account(user["id"]))
    except Exception as e:
        return jsonify({"error": f"could not reset account: {e}"}), 503


@stock_assistant.get("/search")
def search_symbols():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"results": []})
    try:
        quotes = yf.Search(q, max_results=8).quotes
    except Exception as e:
        return jsonify({"error": f"could not search symbols: {e}"}), 502
    results = []
    for r in quotes:
        symbol = r.get("symbol") if isinstance(r, dict) else getattr(r, "symbol", None)
        if not symbol:
            continue
        if isinstance(r, dict):
            name = r.get("longname") or r.get("shortname") or ""
            exchange = r.get("exchDisp") or r.get("exchange") or ""
        else:
            name = getattr(r, "longname", None) or getattr(r, "shortname", None) or ""
            exchange = getattr(r, "exchange", None) or ""
        results.append({"symbol": symbol, "name": name, "exchange": exchange})
    return jsonify({"results": results})


@stock_assistant.get("/prices/<symbol>")
def prices(symbol):
    period = request.args.get("period", "1mo")
    if period not in PRICE_PERIODS:
        return jsonify({
            "error": f"period must be one of: {', '.join(PRICE_PERIODS)}"
        }), 400
    symbol = symbol.upper()
    period_opt, interval = PRICE_PERIODS[period]
    try:
        df = yf.Ticker(symbol).history(period=period_opt, interval=interval, auto_adjust=True)
    except Exception as e:
        return jsonify({"error": f"could not fetch price history for {symbol}: {e}"}), 502
    if df is None or df.empty:
        return jsonify({"error": f"no price history available for {symbol}"}), 404
    df = df[~df.index.isna()]
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()
    points = [
        {
            "datetime": idx.to_pydatetime().isoformat(),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
        }
        for idx, row in df.iterrows()
    ]
    return jsonify({"symbol": symbol, "period": period, "points": points})


@stock_assistant.post("/transfer")
def transfer():
    user = _auth_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    to_email = (data.get("to_email") or "").strip()
    try:
        result = transfer_cash(user["id"], to_email, data.get("amount"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result)


@stock_assistant.get("/transfers")
def transfers_list():
    user = _auth_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, t.amount, t.created_at,
                       CASE WHEN t.from_user_id = %s THEN 'out' ELSE 'in' END AS direction,
                       CASE WHEN t.from_user_id = %s THEN u_to.name ELSE u_from.name END AS counterparty_name,
                       CASE WHEN t.from_user_id = %s THEN u_to.email ELSE u_from.email END AS counterparty_email
                FROM transfers t
                JOIN users u_from ON u_from.id = t.from_user_id
                JOIN users u_to ON u_to.id = t.to_user_id
                WHERE t.from_user_id = %s OR t.to_user_id = %s
                ORDER BY t.created_at DESC, t.id DESC
                LIMIT 20
                """,
                (user["id"], user["id"], user["id"], user["id"], user["id"]),
            )
            rows = cur.fetchall()

    return jsonify(
        [
            {
                "id": r[0],
                "amount": float(r[1]),
                "timestamp": r[2].isoformat(),
                "direction": r[3],
                "counterparty_name": r[4],
                "counterparty_email": r[5],
            }
            for r in rows
        ]
    )


@stock_assistant.get("/recipient")
def recipient():
    user = _auth_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    email = (request.args.get("email") or "").strip()
    result = find_recipient(email)
    if result is None:
        return jsonify({"error": f"no user found with email {email}"}), 404
    return jsonify(result)


# ── Knowledge base management ───────────────────────────────────────

@stock_assistant.get("/kb")
def kb_list():
    if _admin_user() is None:
        return jsonify({"error": "forbidden"}), 403
    try:
        return jsonify(kb.kb_overview())
    except Exception as e:
        return jsonify({"error": f"could not load knowledge base: {e}"}), 503


def _kb_mutation(mutation, *args):
    """Apply a KB mutation (admin required), reload embeddings, return the fresh overview."""
    if _admin_user() is None:
        return jsonify({"error": "forbidden"}), 403
    try:
        mutation(*args)
    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"failed to save: {e}"}), 500
    try:
        kb.reload_kb()
        return jsonify(kb.kb_overview())
    except Exception as e:
        return jsonify({"error": f"saved, but knowledge base reload failed: {e}"}), 503


@stock_assistant.post("/kb/glossary")
def kb_glossary_add():
    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "").strip()
    definition = (data.get("definition") or "").strip()
    if not term or not definition:
        return jsonify({"error": "term and definition are required"}), 400
    return _kb_mutation(kb.add_glossary, term, definition)


@stock_assistant.put("/kb/glossary")
def kb_glossary_update():
    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "").strip()
    definition = (data.get("definition") or "").strip()
    if not term or not definition:
        return jsonify({"error": "term and definition are required"}), 400
    return _kb_mutation(kb.update_glossary, term, definition)


@stock_assistant.delete("/kb/glossary")
def kb_glossary_delete():
    term = (request.args.get("term") or "").strip()
    if not term:
        return jsonify({"error": "term query parameter is required"}), 400
    return _kb_mutation(kb.delete_glossary, term)


@stock_assistant.post("/kb/commentary")
def kb_commentary_add():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    content = (data.get("content") or "").strip()
    if not topic or not content:
        return jsonify({"error": "topic and content are required"}), 400
    return _kb_mutation(kb.add_commentary, topic, content)


@stock_assistant.put("/kb/commentary")
def kb_commentary_update():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    content = (data.get("content") or "").strip()
    if not topic or not content:
        return jsonify({"error": "topic and content are required"}), 400
    return _kb_mutation(kb.update_commentary, topic, content)


@stock_assistant.delete("/kb/commentary")
def kb_commentary_delete():
    topic = (request.args.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "topic query parameter is required"}), 400
    return _kb_mutation(kb.delete_commentary, topic)


@stock_assistant.post("/kb/md")
def kb_md_add():
    data = request.get_json(silent=True) or {}
    file = (data.get("file") or "").strip()
    heading = (data.get("heading") or "").strip()
    content = (data.get("content") or "").strip()
    if not file or not heading or not content:
        return jsonify({"error": "file, heading and content are required"}), 400
    return _kb_mutation(kb.add_md_section, file, heading, content)


@stock_assistant.put("/kb/md")
def kb_md_update():
    data = request.get_json(silent=True) or {}
    file = (data.get("file") or "").strip()
    heading = (data.get("heading") or "").strip()
    content = (data.get("content") or "").strip()
    if not file or not heading or not content:
        return jsonify({"error": "file, heading and content are required"}), 400
    return _kb_mutation(kb.update_md_section, file, heading, content)


@stock_assistant.delete("/kb/md")
def kb_md_delete():
    file = (request.args.get("file") or "").strip()
    heading = (request.args.get("heading") or "").strip()
    if not file or not heading:
        return jsonify({"error": "file and heading query parameters are required"}), 400
    return _kb_mutation(kb.delete_md_section, file, heading)
