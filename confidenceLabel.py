def shared_tokens(a: str, b: str) -> int:
    return len(set(a.split()) & set(b.split()))

def confidence_label(score: float, query: str, candidate: str) -> str:
    overlap = shared_tokens(query, candidate)
    if score >= 90 and overlap >= 2:
        return "high"
    if score >= 75 and overlap >= 1:
        return "medium"
    return "low"