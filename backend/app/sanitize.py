import re

_SCRIPT_BLOCK = re.compile(r"<\s*script\b.*?</\s*script\s*>", re.IGNORECASE | re.DOTALL)
_DANGEROUS_TAGS = re.compile(
    r"<\s*/?\s*(?:script|iframe|object|embed|form|link|meta|style|base)\b[^>]*>",
    re.IGNORECASE,
)
_EVENT_HANDLERS = re.compile(r"""\s+on\w+\s*=\s*(['"]).*?\1""", re.IGNORECASE | re.DOTALL)
_JS_URIS = re.compile(r"""\b(?:javascript|data:text/html)\s*:""", re.IGNORECASE)


def sanitize_text(text: str | None, max_length: int | None = None) -> str | None:
    """Strip common stored-XSS vectors while keeping the rest of the text.

    React renders all doubt fields as plain text (no dangerouslySetInnerHTML),
    so this is defense-in-depth for any raw/HTML consumer of the API.
    """
    if text is None:
        return None
    cleaned = _SCRIPT_BLOCK.sub("", text)
    cleaned = _DANGEROUS_TAGS.sub("", cleaned)
    cleaned = _EVENT_HANDLERS.sub("", cleaned)
    cleaned = _JS_URIS.sub("", cleaned)
    cleaned = cleaned.strip()
    if max_length is not None:
        cleaned = cleaned[:max_length]
    return cleaned
