from typing import Any, Optional
from domain.core.acl.base import BaseTranslator
from domain.core.acl.llm_translator import _scrub_secrets
from domain.core.events import InfrastructureErrorEvent, EventSeverity

class StorageTranslator(BaseTranslator):
    """
    Translator for storage-related exceptions.
    Converts filesystem and database errors into semantic 
    InfrastructureErrorEvent domain events.
    """

    def translate_exception(self, exception: Exception) -> InfrastructureErrorEvent:
        error_msg = str(exception)
        severity = EventSeverity.ERROR
        error_code = "STORAGE_FAILURE"

        # File System Errors
        if isinstance(exception, FileNotFoundError):
            severity = EventSeverity.ERROR
            error_code = "STORAGE_FILE_NOT_FOUND"
        elif isinstance(exception, PermissionError):
            severity = EventSeverity.CRITICAL
            error_code = "STORAGE_PERMISSION_DENIED"
        elif isinstance(exception, IsADirectoryError):
            severity = EventSeverity.ERROR
            error_code = "STORAGE_EXPECTED_FILE_NOT_DIR"

        # Database/SQLAlchemy Errors (String-based check to avoid heavy imports).
        # Check integrity violations first — their messages also contain "sqlite"
        # or "sqlalchemy", so the more specific check must come before the generic one.
        elif "integrity" in error_msg.lower():
            severity = EventSeverity.WARNING
            error_code = "STORAGE_INTEGRITY_VIOLATION"
        elif "sqlalchemy" in error_msg.lower() or "sqlite" in error_msg.lower():
            severity = EventSeverity.ERROR
            error_code = "STORAGE_DATABASE_FAILURE"

        # Generic fallback
        elif "oserror" in error_msg.lower():
            error_code = "STORAGE_OS_LEVEL_FAILURE"

        return InfrastructureErrorEvent(
            severity=severity,
            source="Storage_Infrastructure",
            error_code=error_code,
            original_exception=_scrub_secrets(error_msg),
            metadata={"exception_type": type(exception).__name__}
        )

    def transform_data(self, raw_data: Any) -> Any:
        """
        Converts raw data from files or databases into clean domain-ready formats.
        """
        if isinstance(raw_data, str):
            return raw_data.strip()
        if isinstance(raw_data, bytes):
            return raw_data.decode('utf-8', errors='ignore').strip()
        return raw_data
