import json
import os
import re
from pathlib import Path

from google import genai

from ....gemini import get_client
from .embeddings import embed_texts, search_embeddings

KB_DIR = str(Path(__file__).resolve().parent.parent / "data" / "knowledge_base")
GLOSSARY_FILE = os.path.join(KB_DIR, "glossary.json")
COMMENTARY_FILE = os.path.join(KB_DIR, "commentary.json")

_kb_instance = None


def load_json_entries(path, label):
    with open(path) as f:
        entries = json.load(f)
    if label == "Glossary":
        return [f"Term: {e['term']}\nDefinition: {e['definition']}" for e in entries]
    return [f"Topic: {e['topic']}\nContent: {e['content']}" for e in entries]


def load_markdown_entries(filepath):
    entries = []
    with open(filepath) as f:
        raw = f.read()

    current_heading = None
    current_body = []
    for line in raw.split("\n"):
        m = re.match(r"^## (.+)$", line)
        if m:
            if current_heading:
                body = "\n".join(current_body).strip()
                entries.append(f"Topic: {current_heading}\nContent: {body}")
            current_heading = m.group(1).strip()
            current_body = []
        else:
            current_body.append(line)
    if current_heading:
        body = "\n".join(current_body).strip()
        entries.append(f"Topic: {current_heading}\nContent: {body}")

    return entries


class KnowledgeBase:
    def __init__(self, client: genai.Client):
        self.client = client
        self.chunks: list[str] = []
        self.embeddings: list = []
        self.sources: list[str] = []

    def load(self):
        self.chunks = []
        self.embeddings = []
        self.sources = []

        glossary_path = os.path.join(KB_DIR, "glossary.json")
        commentary_path = os.path.join(KB_DIR, "commentary.json")

        pairs = []
        if os.path.exists(glossary_path):
            pairs.append((glossary_path, "Glossary"))
        if os.path.exists(commentary_path):
            pairs.append((commentary_path, "Commentary"))

        for path, label in pairs:
            entries = load_json_entries(path, label)
            self.chunks.extend(entries)
            self.sources.extend([label] * len(entries))

        for fname in sorted(os.listdir(KB_DIR)):
            if fname.endswith(".md"):
                fpath = os.path.join(KB_DIR, fname)
                entries = load_markdown_entries(fpath)
                self.chunks.extend(entries)
                self.sources.extend([f"Markdown ({fname})"] * len(entries))

        if self.chunks:
            self.embeddings = embed_texts(self.client, self.chunks)

    def search(self, query: str, top_k: int = 3) -> str:
        if not self.chunks:
            return "Knowledge base is empty. No content loaded."

        results = search_embeddings(query, self.chunks, self.embeddings, self.client, top_k)
        lines = ["Knowledge Base Results:", ""]
        for idx, text, score in results:
            lines.append(f"[{idx}] Relevance: {score:.2%} | Source: {self.sources[idx]}")
            lines.append(text)
            lines.append("")
        return "\n".join(lines)


def get_kb() -> KnowledgeBase | None:
    global _kb_instance
    return _kb_instance


def init_kb(client: genai.Client) -> KnowledgeBase:
    global _kb_instance
    _kb_instance = KnowledgeBase(client)
    _kb_instance.load()
    return _kb_instance


# ── KB lifecycle (management page) ──────────────────────────────────

def ensure_kb() -> KnowledgeBase:
    """Lazily initialize the KB (with the project client) so it can be used
    before the agent has ever been invoked."""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase(get_client())
        _kb_instance.load()
    return _kb_instance


def reload_kb() -> KnowledgeBase:
    """Re-load and re-embed the knowledge base after a mutation."""
    global _kb_instance
    if _kb_instance is None:
        return ensure_kb()
    _kb_instance.load()
    return _kb_instance


def kb_overview() -> dict:
    """Grouped listing of all KB content plus embedding status."""
    kb = ensure_kb()
    return {
        "glossary": get_glossary(),
        "commentary": _load_json(COMMENTARY_FILE),
        "markdown": [
            {"file": fname, "sections": get_markdown_sections(fname)}
            for fname in list_markdown_files()
        ],
        "chunks": len(kb.chunks),
        "embedded": len(kb.embeddings) > 0,
    }


# ── JSON helpers ────────────────────────────────────────────────────

def _load_json(path) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_json(path, entries):
    with open(path, "w", encoding="utf-8", newline="") as f:
        json.dump(entries, f, indent=2)
        f.write("\n")


def _find_entry(entries, key, search):
    for e in entries:
        if str(e[key]).lower() == str(search).lower():
            return e
    return None


# ── Glossary CRUD ───────────────────────────────────────────────────

def get_glossary() -> list[dict]:
    return _load_json(GLOSSARY_FILE)


def add_glossary(term: str, definition: str) -> list[dict]:
    entries = _load_json(GLOSSARY_FILE)
    if _find_entry(entries, "term", term):
        raise ValueError(f"term '{term}' already exists")
    entries.append({"term": term, "definition": definition})
    _save_json(GLOSSARY_FILE, entries)
    return entries


def update_glossary(term: str, definition: str) -> list[dict]:
    entries = _load_json(GLOSSARY_FILE)
    entry = _find_entry(entries, "term", term)
    if entry is None:
        raise KeyError(f"term '{term}' not found")
    entry["definition"] = definition
    _save_json(GLOSSARY_FILE, entries)
    return entries


def delete_glossary(term: str) -> list[dict]:
    entries = _load_json(GLOSSARY_FILE)
    if _find_entry(entries, "term", term) is None:
        raise KeyError(f"term '{term}' not found")
    entries = [e for e in entries if e["term"].lower() != term.lower()]
    _save_json(GLOSSARY_FILE, entries)
    return entries


# ── Commentary CRUD ─────────────────────────────────────────────────

def get_commentary() -> list[dict]:
    return _load_json(COMMENTARY_FILE)


def add_commentary(topic: str, content: str) -> list[dict]:
    entries = _load_json(COMMENTARY_FILE)
    if _find_entry(entries, "topic", topic):
        raise ValueError(f"topic '{topic}' already exists")
    entries.append({"topic": topic, "content": content})
    _save_json(COMMENTARY_FILE, entries)
    return entries


def update_commentary(topic: str, content: str) -> list[dict]:
    entries = _load_json(COMMENTARY_FILE)
    entry = _find_entry(entries, "topic", topic)
    if entry is None:
        raise KeyError(f"topic '{topic}' not found")
    entry["content"] = content
    _save_json(COMMENTARY_FILE, entries)
    return entries


def delete_commentary(topic: str) -> list[dict]:
    entries = _load_json(COMMENTARY_FILE)
    if _find_entry(entries, "topic", topic) is None:
        raise KeyError(f"topic '{topic}' not found")
    entries = [e for e in entries if e["topic"].lower() != topic.lower()]
    _save_json(COMMENTARY_FILE, entries)
    return entries


# ── Markdown sections CRUD ──────────────────────────────────────────

def list_markdown_files() -> list[str]:
    if not os.path.isdir(KB_DIR):
        return []
    return sorted(
        f for f in os.listdir(KB_DIR) if f.endswith(".md") and f != "README.md"
    )


def _parse_md(filepath) -> list[list[str]]:
    entries: list[list[str]] = []
    with open(filepath, encoding="utf-8") as f:
        raw = f.read()

    current_heading = None
    current_body = []
    for line in raw.split("\n"):
        m = re.match(r"^## (.+)$", line)
        if m:
            if current_heading:
                body = "\n".join(current_body).strip()
                entries.append([current_heading, body])
            current_heading = m.group(1).strip()
            current_body = []
        else:
            current_body.append(line)
    if current_heading:
        body = "\n".join(current_body).strip()
        entries.append([current_heading, body])

    return entries


def _rebuild_md(entries) -> str:
    lines = []
    for heading, body in entries:
        lines.append(f"## {heading}")
        if body:
            lines.append(body)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _md_path(filename: str) -> str:
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
    path = os.path.join(KB_DIR, filename)
    if not os.path.exists(path):
        raise KeyError(f"markdown file '{filename}' not found")
    return path


def get_markdown_sections(filename: str) -> list[dict]:
    return [
        {"heading": h, "content": c}
        for h, c in _parse_md(_md_path(filename))
    ]


def add_md_section(filename: str, heading: str, content: str) -> list[dict]:
    path = _md_path(filename)
    entries = _parse_md(path)
    if any(h.lower() == heading.lower() for h, _ in entries):
        raise ValueError(f"heading '{heading}' already exists in {filename}")
    entries.append([heading, content])
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(_rebuild_md(entries))
    return get_markdown_sections(filename)


def update_md_section(filename: str, heading: str, content: str) -> list[dict]:
    path = _md_path(filename)
    entries = _parse_md(path)
    for entry in entries:
        if entry[0].lower() == heading.lower():
            entry[1] = content
            break
    else:
        raise KeyError(f"heading '{heading}' not found in {filename}")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(_rebuild_md(entries))
    return get_markdown_sections(filename)


def delete_md_section(filename: str, heading: str) -> list[dict]:
    path = _md_path(filename)
    entries = _parse_md(path)
    if not any(h.lower() == heading.lower() for h, _ in entries):
        raise KeyError(f"heading '{heading}' not found in {filename}")
    entries = [e for e in entries if e[0].lower() != heading.lower()]
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(_rebuild_md(entries))
    return get_markdown_sections(filename)
