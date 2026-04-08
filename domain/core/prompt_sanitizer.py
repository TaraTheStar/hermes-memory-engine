"""
Sanitization utilities for untrusted data interpolated into LLM prompts.

Wraps user-controlled content in XML-style delimiters so the model can
distinguish system instructions from data, and caps the length to prevent
prompt stuffing.
"""

_MAX_FIELD_LENGTH = 2000


import re

_XML_TAG_PATTERN = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9_-]*)')


def sanitize_field(value: str, tag: str, max_length: int = _MAX_FIELD_LENGTH) -> str:
    """Wrap *value* in ``<tag>...</tag>`` delimiters after length-capping.

    All XML-style tags in *value* are escaped so injection of arbitrary
    semantic boundaries (``<system>``, ``<instruction>``, etc.) is prevented,
    not just the specific closing tag for *tag*.
    """
    text = str(value) if value is not None else ""
    if len(text) > max_length:
        text = text[:max_length] + "... [truncated]"
    # Escape all XML-like opening/closing tags to prevent boundary spoofing
    text = _XML_TAG_PATTERN.sub(r'<\\\1\2', text)
    return f"<{tag}>{text}</{tag}>"
