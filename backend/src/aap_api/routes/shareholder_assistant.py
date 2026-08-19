import hashlib
import json
import re
from pathlib import Path

import faiss
import numpy as np
import psycopg
from docx import Document
from flask import Blueprint, jsonify, request
from google.genai import types
from pypdf import PdfReader

from ..db import get_conn_string
from ..gemini import get_client
from .auth import get_current_user

shareholder_assistant = Blueprint(
    "shareholder_assistant", __name__, url_prefix="/api/shareholder-assistant"
)

DOCUMENTS_DIR = Path(__file__).resolve().parents[3] / "data" / "shareholder_documents"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
VECTOR_STORE = {
    "chunks": [],
    "sources": [],
    "index": None,
}


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_indexed_documents_from_db():
    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id, d.file_name, d.file_path, d.file_hash, d.chunk_count
                FROM shareholder_documents d
                ORDER BY d.file_path
                """
            )
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "file_name": row[1],
            "file_path": row[2],
            "file_hash": row[3],
            "chunk_count": row[4],
        }
        for row in rows
    ]


def _load_document_chunks_from_db(document_id: int):
    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT chunk_index, chunk_text, embedding_vector
                FROM shareholder_document_chunks
                WHERE document_id = %s
                ORDER BY chunk_index
                """,
                (document_id,),
            )
            rows = cur.fetchall()

    return [
        {
            "chunk_index": row[0],
            "chunk_text": row[1],
            "embedding_vector": row[2],
        }
        for row in rows
    ]


def _save_document_chunks_to_db(file_path: str, file_name: str, chunks, embedding_vectors):
    file_hash = _hash_file(DOCUMENTS_DIR / file_path)

    with psycopg.connect(get_conn_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO shareholder_documents (file_name, file_path, file_hash, chunk_count, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (file_path)
                DO UPDATE SET
                    file_name = EXCLUDED.file_name,
                    file_hash = EXCLUDED.file_hash,
                    chunk_count = EXCLUDED.chunk_count,
                    updated_at = now()
                RETURNING id
                """,
                (file_name, file_path, file_hash, len(chunks)),
            )
            document_id = cur.fetchone()[0]

            cur.execute(
                "DELETE FROM shareholder_document_chunks WHERE document_id = %s",
                (document_id,),
            )

            for index, (chunk_text, embedding_vector) in enumerate(zip(chunks, embedding_vectors)):
                cur.execute(
                    """
                    INSERT INTO shareholder_document_chunks (document_id, chunk_index, chunk_text, embedding_vector)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (document_id, index, chunk_text, json.dumps(embedding_vector.tolist())),
                )


def _ensure_directory():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def _read_text_file(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return "\n\n".join(pages)

    if suffix == ".docx":
        document = Document(str(path))
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        return "\n\n".join(paragraphs)

    return ""


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 180):
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []

    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(start + max_chars - overlap, end - max_chars + overlap)

    return chunks


def _embed_texts(texts):
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    client = get_client()
    vectors = []

    for i in range(0, len(texts), 100):
        batch = texts[i : i + 100]
        response = client.models.embed_content(model="gemini-embedding-001", contents=batch)
        for embedding in response.embeddings:
            values = getattr(embedding, "values", None)
            if values is None and hasattr(embedding, "__dict__"):
                values = embedding.__dict__.get("values")
            vectors.append(np.asarray(values, dtype=np.float32))

    if not vectors:
        return np.empty((0, 0), dtype=np.float32)

    return np.vstack(vectors).astype(np.float32)


def _build_vector_store(force_rebuild: bool = False):
    global VECTOR_STORE

    _ensure_directory()
    files = sorted(
        path for path in DOCUMENTS_DIR.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        VECTOR_STORE = {"chunks": [], "sources": [], "index": None}
        return VECTOR_STORE

    if not force_rebuild and VECTOR_STORE["index"] is not None and VECTOR_STORE["chunks"]:
        return VECTOR_STORE

    db_documents = _load_indexed_documents_from_db()
    db_lookup = {record["file_path"]: record for record in db_documents}
    chunks = []
    sources = []
    embeddings_to_save = []

    for file_path in files:
        relative_path = str(file_path.relative_to(DOCUMENTS_DIR)).replace('\\', '/')
        file_hash = _hash_file(file_path)
        persisted = db_lookup.get(relative_path)

        if not force_rebuild and persisted and persisted["file_hash"] == file_hash and persisted["chunk_count"] > 0:
            db_chunks = _load_document_chunks_from_db(persisted["id"])
            for chunk_row in db_chunks:
                chunks.append(chunk_row["chunk_text"])
                sources.append(file_name := file_path.name)
                embeddings_to_save.append(np.asarray(chunk_row["embedding_vector"], dtype=np.float32))
            continue

        text = _read_text_file(file_path)
        file_chunks = _chunk_text(text)
        if not file_chunks:
            continue

        if file_chunks:
            embeddings = _embed_texts(file_chunks)
            if embeddings.size:
                _save_document_chunks_to_db(relative_path, file_path.name, file_chunks, embeddings)
            for chunk_text, embedding_vector in zip(file_chunks, embeddings):
                chunks.append(chunk_text)
                sources.append(file_path.name)
                embeddings_to_save.append(np.asarray(embedding_vector, dtype=np.float32))

    VECTOR_STORE = {"chunks": chunks, "sources": sources, "index": None}

    if not chunks:
        return VECTOR_STORE

    embeddings = np.vstack(embeddings_to_save).astype(np.float32)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    VECTOR_STORE["index"] = index
    return VECTOR_STORE


def _search_documents(query: str, top_k: int = 5):
    store = _build_vector_store()
    if not store["chunks"] or store["index"] is None:
        return []

    query_vector = _embed_texts([query])
    if query_vector.size == 0:
        return []

    faiss.normalize_L2(query_vector)
    scores, indices = store["index"].search(query_vector, min(top_k, len(store["chunks"])))

    results = []
    for score, index_position in zip(scores[0], indices[0]):
        if index_position < 0:
            continue
        results.append(
            {
                "score": float(score),
                "source": store["sources"][int(index_position)],
                "chunk": store["chunks"][int(index_position)],
            }
        )
    return results


def _generate_answer(query: str, matches):
    if not matches:
        return (
            "I couldn't find any relevant content in the annual report folder. "
            "Add .txt, .md, .pdf, or .docx files to the project folder at "
            f"{DOCUMENTS_DIR} and try again."
        )

    context = "\n\n".join(
        f"[Source: {match['source']}]\n{match['chunk'][:1200].strip()}" for match in matches[:5]
    )

    system_instruction = (
        "You are a shareholder assistant for annual reports. Answer the user's question using only the supplied excerpts. "
        "Write clear, concise, business-friendly answers. Cite the source document names in your answer. "
        "If the excerpts do not contain enough information, say so directly rather than fabricating details. "
        "Do not list raw chunks or quote large blocks of text. Summarise and interpret the information."
    )

    prompt = (
        f"Question: {query}\n\nRelevant annual report excerpts:\n{context}"
    )

    try:
        client = get_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
        )

        if not response or not getattr(response, "candidates", None):
            raise ValueError("Empty Gemini response")

        parts = []
        for candidate in response.candidates:
            for part in getattr(candidate.content, "parts", []) or []:
                if getattr(part, "text", None):
                    parts.append(part.text)

        if parts:
            answer = "\n".join(parts).strip()
            if answer:
                return answer

        if hasattr(response, "text") and response.text:
            return response.text.strip()

    except Exception:
        pass

    summary_parts = []
    for match in matches[:3]:
        summary_parts.append(f"{match['source']}: {match['chunk'][:300].strip()}")
    return "Based on the annual report excerpts, here is the relevant context:\n\n" + "\n\n".join(summary_parts)


@shareholder_assistant.get("/health")
def health():
    _ensure_directory()
    store = _build_vector_store()
    return jsonify(
        {
            "status": "ok",
            "service": "shareholder-assistant",
            "documents_dir": str(DOCUMENTS_DIR),
            "indexed_chunks": len(store["chunks"]),
            "ready": bool(store["chunks"]),
        }
    )


@shareholder_assistant.get("/documents")
def documents():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    _ensure_directory()
    files = []
    for file_path in sorted(DOCUMENTS_DIR.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(
                {
                    "name": file_path.name,
                    "path": str(file_path.relative_to(DOCUMENTS_DIR)),
                    "size": file_path.stat().st_size,
                }
            )

    store = _build_vector_store()
    ready = bool(files) and bool(store["chunks"]) and len(store["chunks"]) > 0
    return jsonify({
        "documents": files,
        "document_count": len(files),
        "chunk_count": len(store["chunks"]),
        "documents_dir": str(DOCUMENTS_DIR),
        "ready": ready,
    })


@shareholder_assistant.post("/reindex")
def reindex():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    store = _build_vector_store(force_rebuild=True)
    ready = bool(store["chunks"])
    return jsonify({
        "status": "reindexed",
        "document_count": len({item for item in store["sources"]}),
        "chunk_count": len(store["chunks"]),
        "ready": ready,
    })


@shareholder_assistant.post("/chat")
def chat():
    user = get_current_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    matches = _search_documents(message, top_k=5)
    answer = _generate_answer(message, matches)

    return jsonify(
        {
            "answer": answer,
            "sources": [match["source"] for match in matches],
            "match_count": len(matches),
            "documents_dir": str(DOCUMENTS_DIR),
        }
    )
