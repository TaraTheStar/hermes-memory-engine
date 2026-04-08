"""Tests for ACL translator paths not covered by existing tests."""
from domain.core.acl.llm_translator import LLMTranslator, _scrub_secrets
from domain.core.acl.storage_translator import StorageTranslator
from domain.core.events import EventSeverity


class TestScrubSecrets:
    def test_api_key_redacted(self):
        msg = "Error authenticating with key sk-abcdefghijklmnopqrstuvwx"
        result = _scrub_secrets(msg)
        assert "sk-abcdefghijklmnopqrstuvwx" not in result
        assert "[REDACTED]" in result

    def test_bearer_token_redacted(self):
        msg = "Auth header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc"
        result = _scrub_secrets(msg)
        assert "eyJhbG" not in result
        assert "[REDACTED]" in result

    def test_no_secret_unchanged(self):
        msg = "Simple error message with no secrets"
        result = _scrub_secrets(msg)
        assert result == msg

    def test_hex_string_redacted(self):
        msg = "Token: " + "a" * 40
        result = _scrub_secrets(msg)
        assert "a" * 40 not in result


class TestLLMTranslatorMRO:
    def test_subclass_of_known_type_matched(self):
        """A subclass of ConnectionError should match via MRO."""
        class CustomConnectionError(ConnectionError):
            pass

        translator = LLMTranslator()
        event = translator.translate_exception(CustomConnectionError("failed"))
        assert event.error_code == "LLM_CONNECTION_TIMEOUT"


class TestStorageTranslatorMissingPaths:
    def test_integrity_error(self):
        """IntegrityError-like exception should map to STORAGE_INTEGRITY_VIOLATION."""
        translator = StorageTranslator()
        exc = Exception("(sqlite3.IntegrityError) UNIQUE constraint failed")
        event = translator.translate_exception(exc)
        assert event.error_code == "STORAGE_INTEGRITY_VIOLATION"
        assert event.severity == EventSeverity.WARNING

    def test_transform_data_bytes(self):
        translator = StorageTranslator()
        result = translator.transform_data(b"hello bytes")
        assert isinstance(result, str)
