from .registry import tool
from ..rag.knowledge_base import get_kb


@tool(category="knowledge")
def search_knowledge_base(query: str) -> str:
    """Search the investment knowledge base for terms, concepts, and market commentary. Use this to look up financial terms, investment strategies, and market analysis concepts."""
    kb = get_kb()
    if kb is None:
        return "Knowledge base not initialized."
    return kb.search(query)
