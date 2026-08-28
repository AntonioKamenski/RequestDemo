import re

def normalize(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.lower()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s