import re
from typing import Any, Optional
from domain.core.acl.base import BaseTranslator
from domain.core.events import InfrastructureErrorEvent, EventSeverity

# Matches common API key patterns (sk-..., key-..., bearer tokens, hex/alnum strings)
_SECRET_PATTERN = re.compile(
    r'(sk-[a-zA-Z0-9]{8,}|key-[a-zA-Z0-9]{8,}|Bearer\s+\S{12,}|[a-fA-F0-9]{32,}|[a-zA-Z0-9_-]{40,})',
)


def _scrub_secrets(msg: str) -> str:
    """Replace probable secrets in an error message with a redaction marker."""
    return _SECRET_PATTERN.sub("[REDACTED]", msg)


class LLMTranslator(BaseTranslator):
    """
    Translator for LLM-related exceptions.
    Converts technical API errors (OpenAI, connection errors, etc.)
    into semantic InfrastructureErrorEvent domain events.
    """

    # Map exception class names to (severity, error_code).
    # Using class names avoids importing every provider SDK while being
    # more reliable than substring matching on the message body.
    _TYPE_MAP = {
        "AuthenticationError": (EventSeverity.CRITICAL, "LLM_AUTH_FAILURE"),
        "RateLimitError":      (EventSeverity.WARNING,  "LLM_RATE_LIMIT"),
        "APIConnectionError":  (EventSeverity.ERROR,    "LLM_CONNECTION_TIMEOUT"),
        "Timeout":             (EventSeverity.ERROR,    "LLM_CONNECTION_TIMEOUT"),
        "TimeoutError":        (EventSeverity.ERROR,    "LLM_CONNECTION_TIMEOUT"),
        "ConnectionError":     (EventSeverity.ERROR,    "LLM_CONNECTION_TIMEOUT"),
        "BadRequestError":     (EventSeverity.ERROR,    "LLM_INVALID_REQUEST"),
        "InvalidRequestError": (EventSeverity.ERROR,    "LLM_INVALID_REQUEST"),
    }

    def translate_exception(self, exception: Exception) -> InfrastructureErrorEvent:
        severity = EventSeverity.ERROR
        error_code = "LLM_API_FAILURE"

        # Walk the MRO so subclasses of known types are also matched
        for cls in type(exception).__mro__:
            if cls.__name__ in self._TYPE_MAP:
                severity, error_code = self._TYPE_MAP[cls.__name__]
                break

        return InfrastructureErrorEvent(
            severity=severity,
            source="LLM_Infrastructure",
            error_code=error_code,
            original_exception=_scrub_secrets(str(exception)),
            metadata={"exception_type": type(exception).__name__}
        )

    def transform_data(self, raw_data: Any) -> Any:
        """
        For LLM, data transformation might involve cleaning whitespace 
        or verifying the structure of a JSON response.
        """
        if isinstance(raw_data, str):
            return raw_data.strip()
        return raw_data
