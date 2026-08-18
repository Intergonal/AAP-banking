import numpy as np
from google import genai

EMBED_MODEL = "gemini-embedding-001"


def embed_texts(client: genai.Client, texts: list[str]) -> list[np.ndarray]:
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
    )
    return [np.array(e.values, dtype=np.float32) for e in result.embeddings]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = float(np.dot(a, b))
    norm = float(np.linalg.norm(a)) * float(np.linalg.norm(b))
    if norm == 0:
        return 0.0
    return dot / norm


def search_embeddings(
    query: str,
    stored_texts: list[str],
    stored_embeddings: list[np.ndarray],
    client: genai.Client,
    top_k: int = 3,
) -> list[tuple[int, str, float]]:
    query_emb = embed_texts(client, [query])[0]
    scores = [(i, cosine_similarity(query_emb, stored_embeddings[i])) for i in range(len(stored_texts))]
    scores.sort(key=lambda x: -x[1])
    return [(scores[i][0], stored_texts[scores[i][0]], scores[i][1]) for i in range(min(top_k, len(scores)))]
