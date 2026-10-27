import os
import re

FAQ_PATH = os.path.join(os.path.dirname(__file__), "../../data/faq_knowledge_base.md")

_docs = None

def load_faq_docs():
    global _docs
    if _docs is None:
        if os.path.exists(FAQ_PATH):
            with open(FAQ_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            # Split sections by heading
            sections = re.split(r'\n(?=## )', content)
            _docs = [s.strip() for s in sections if s.strip()]
        else:
            _docs = []
    return _docs

def query_faq_context(query: str, top_k: int = 2) -> str:
    """
    Retrieves the most relevant FAQ knowledge base sections for a customer support ticket.
    """
    docs = load_faq_docs()
    if not docs:
        return "Standard e-commerce 30-day return policy and shipping support applies."

    query_lower = query.lower()

    # Score docs based on keyword overlap
    scored_docs = []
    for doc in docs:
        score = 0
        words = re.findall(r'\w+', query_lower)
        for w in words:
            if len(w) > 3 and w in doc.lower():
                score += 1
        scored_docs.append((score, doc))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    best_docs = [d[1] for d in scored_docs[:top_k]]
    return "\n\n".join(best_docs)
