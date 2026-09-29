import re

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "is", "are", "was", "were", "be", "been",
    "to", "of", "in", "on", "for", "with", "my", "your", "its", "it", "this", "that",
    "i", "you", "we", "they", "do", "does", "did", "not", "can", "cant", "why", "what",
    "how", "when", "where", "have", "has", "had", "am", "at", "if", "from", "as", "will",
    "would", "could", "should", "please", "help", "thanks", "question",
}

_TEXT_TOKEN_RE = re.compile(r"[a-z0-9]+")
_CODE_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT_RE = re.compile(r"(?:#|//).*$", re.M)


def _tokenize_text(text: str) -> set[str]:
    words = _TEXT_TOKEN_RE.findall(text.lower())
    return {w for w in words if w not in _STOPWORDS}


def _tokenize_code(code: str) -> list[str]:
    code = _BLOCK_COMMENT_RE.sub("", code)
    code = _LINE_COMMENT_RE.sub("", code)
    return _CODE_TOKEN_RE.findall(code.lower())


def _shingles(tokens: list[str], k: int = 5) -> set[tuple[str, ...]]:
    if len(tokens) < k:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def text_similarity(text_a: str, text_b: str) -> float:
    return jaccard(_tokenize_text(text_a), _tokenize_text(text_b))


def code_similarity(code_a: str, code_b: str) -> float:
    return jaccard(_shingles(_tokenize_code(code_a)), _shingles(_tokenize_code(code_b)))
