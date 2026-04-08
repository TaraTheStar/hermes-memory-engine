import pytest

from domain.core.acl.llm_translator import LLMTranslator
from domain.core.acl.storage_translator import StorageTranslator
from domain.core.events import EventSeverity


class TestLLMTranslator:
    @pytest.fixture
    def translator(self):
        return LLMTranslator()

    def test_connection_error(self, translator):
        exc = ConnectionError("ConnectionError: server unreachable")
        event = translator.translate_exception(exc)
        assert event.error_code == "LLM_CONNECTION_TIMEOUT"
        assert event.severity == EventSeverity.ERROR

    def test_auth_error(self, translator):
        exc = Exception("AuthenticationError: invalid api_key")
        event = translator.translate_exception(exc)
        assert event.error_code == "LLM_AUTH_FAILURE"
        assert event.severity == EventSeverity.CRITICAL

    def test_rate_limit(self, translator):
        exc = Exception("RateLimitError: 429 Too Many Requests")
        event = translator.translate_exception(exc)
        assert event.error_code == "LLM_RATE_LIMIT"
        assert event.severity == EventSeverity.WARNING

    def test_invalid_request(self, translator):
        exc = Exception("InvalidRequestError: 400 bad prompt")
        event = translator.translate_exception(exc)
        assert event.error_code == "LLM_INVALID_REQUEST"

    def test_generic_fallback(self, translator):
        exc = Exception("something completely unexpected")
        event = translator.translate_exception(exc)
        assert event.error_code == "LLM_API_FAILURE"

    def test_transform_data_strips_whitespace(self, translator):
        assert translator.transform_data("  hello  ") == "hello"

    def test_transform_data_passthrough(self, translator):
        assert translator.transform_data(42) == 42


class TestStorageTranslator:
    @pytest.fixture
    def translator(self):
        return StorageTranslator()

    def test_file_not_found(self, translator):
        event = translator.translate_exception(FileNotFoundError("missing.db"))
        assert event.error_code == "STORAGE_FILE_NOT_FOUND"

    def test_permission_error(self, translator):
        event = translator.translate_exception(PermissionError("denied"))
        assert event.error_code == "STORAGE_PERMISSION_DENIED"
        assert event.severity == EventSeverity.CRITICAL

    def test_is_a_directory(self, translator):
        event = translator.translate_exception(IsADirectoryError("/tmp"))
        assert event.error_code == "STORAGE_EXPECTED_FILE_NOT_DIR"

    def test_sqlalchemy_error(self, translator):
        event = translator.translate_exception(Exception("sqlalchemy.exc.OperationalError"))
        assert event.error_code == "STORAGE_DATABASE_FAILURE"

    def test_generic_fallback(self, translator):
        event = translator.translate_exception(RuntimeError("boom"))
        assert event.error_code == "STORAGE_FAILURE"

    def test_transform_data_strips_string(self, translator):
        assert translator.transform_data("  data  ") == "data"

    def test_transform_data_decodes_bytes(self, translator):
        assert translator.transform_data(b"  bytes  ") == "bytes"

    def test_transform_data_passthrough(self, translator):
        assert translator.transform_data([1, 2]) == [1, 2]
