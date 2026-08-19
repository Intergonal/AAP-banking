import os

import psycopg
import torch
from flask import Blueprint, jsonify, request
from transformers import AutoModelForTokenClassification, AutoTokenizer

from ..db import get_conn_string
from .auth import get_current_user

pii_redaction = Blueprint("pii_redaction", __name__, url_prefix="/api/pii-redaction")
MODEL_REPO_ID = os.getenv("PII_MODEL_REPO_ID", "240732X/pii-redaction-model")

_model = None
_tokenizer = None
_device = None


def _current_user_id():
    user = get_current_user()
    if user is None:
        return None
    return int(user["id"])


def _load_model():
    global _model, _tokenizer, _device
    if _model is None or _tokenizer is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _model = AutoModelForTokenClassification.from_pretrained(MODEL_REPO_ID)
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_REPO_ID)
        _model.to(_device)
        _model.eval()
    return _model, _tokenizer, _device


def _placeholder_for_label(label: str) -> str:
    value = (label or "").upper().replace("B-", "").replace("I-", "")
    markers = (
        ("NAME_STUDENT", "NAME"),
        ("NAME", "NAME"),
        ("ID_NUM", "ID-NUM"),
        ("ID", "ID-NUM"),
        ("PHONE_NUM", "PHONE"),
        ("PHONE", "PHONE"),
        ("EMAIL", "EMAIL"),
        ("URL_PERSONAL", "URL"),
        ("URL", "URL"),
        ("USERNAME", "USERNAME"),
        ("STREET_ADDRESS", "ADDRESS"),
        ("ADDRESS", "ADDRESS"),
        ("DATE", "DATE"),
    )
    for needle, replacement in markers:
        if needle in value:
            return replacement
    return "REDACTED"


def _redact_pii_text(text: str) -> str:
    model, tokenizer, device = _load_model()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        predictions = torch.argmax(outputs.logits, dim=2)

    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0].cpu())
    id2tag = model.config.id2label
    pred_tags = [id2tag[p.item()] for p in predictions[0].cpu()]
    offsets = tokenizer(text, return_offsets_mapping=True, truncation=True, max_length=512)["offset_mapping"]

    token_spans = []
    for i, (offset, tag) in enumerate(zip(offsets, pred_tags)):
        if tokens[i] in ["[CLS]", "[SEP]", "[PAD]"]:
            continue
        if offset[0] == offset[1]:
            continue
        token_spans.append((offset[0], offset[1], tag))

    merged_spans = []
    current_start = current_end = current_tag = None
    for start, end, tag in token_spans:
        if tag == "O":
            if current_tag is not None:
                merged_spans.append((current_start, current_end, current_tag))
                current_tag = None
            merged_spans.append((start, end, "O"))
        else:
            if current_tag is None:
                current_start, current_end, current_tag = start, end, tag
            else:
                if tag.startswith("I-") or tag == current_tag:
                    current_end = end
                else:
                    merged_spans.append((current_start, current_end, current_tag))
                    current_start, current_end, current_tag = start, end, tag

    if current_tag is not None:
        merged_spans.append((current_start, current_end, current_tag))

    redacted_chars = []
    last_end = 0
    for start, end, tag in merged_spans:
        redacted_chars.append(text[last_end:start])
        if tag == "O":
            redacted_chars.append(text[start:end])
        else:
            placeholder = _placeholder_for_label(tag)
            redacted_chars.append(f"[{placeholder}]")
        last_end = end

    redacted_chars.append(text[last_end:])
    return "".join(redacted_chars)


def _save_history(user_id, original_text, redacted_text, file_name=None):
    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pii_redaction_history (user_id, file_name, original_text, redacted_text)
                VALUES (%s, %s, %s, %s)
                RETURNING id, user_id, file_name, original_text, redacted_text, created_at
                """,
                (user_id, file_name, original_text, redacted_text),
            )
            row = cur.fetchone()
    return {
        "id": row[0],
        "user_id": row[1],
        "file_name": row[2],
        "original_text": row[3],
        "redacted_text": row[4],
        "created_at": row[5].isoformat() if row[5] else None,
    }


@pii_redaction.get("/health")
def health():
    return jsonify({"status": "ok", "service": "pii-redaction"})


@pii_redaction.get("/history")
def history():
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({"error": "unauthorized"}), 401

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, file_name, original_text, redacted_text, created_at
                FROM pii_redaction_history
                WHERE user_id = %s
                ORDER BY created_at DESC, id DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()

    entries = []
    for row in rows:
        entries.append(
            {
                "id": row[0],
                "file_name": row[1],
                "original_text": row[2],
                "redacted_text": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
            }
        )
    return jsonify(entries)


@pii_redaction.delete("/history/<int:entry_id>")
def delete_history(entry_id):
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({"error": "unauthorized"}), 401

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM pii_redaction_history WHERE id = %s AND user_id = %s",
                (entry_id, user_id),
            )
            deleted = cur.rowcount > 0
    if not deleted:
        return jsonify({"error": "history entry not found"}), 404
    return jsonify({"deleted": True})


@pii_redaction.post("/redact")
def redact():
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    file_name = data.get("file_name")

    try:
        redacted_text = _redact_pii_text(text)
        saved = _save_history(user_id, text, redacted_text, file_name)
    except Exception as exc:
        return jsonify({"error": f"Failed to redact text: {exc}"}), 502

    return jsonify(
        {
            "redacted_text": redacted_text,
            "model": MODEL_REPO_ID,
            "entities": [],
            "saved_history": saved,
        }
    )
