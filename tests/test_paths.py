"""Tests for infrastructure/paths.py path resolution."""
import os
import pytest
from unittest.mock import patch
from infrastructure.paths import (
    _base_dir, default_structural_db, default_semantic_dir,
    _LOCAL_BASE, _validate_data_path,
)


class TestBaseDir:
    def test_explicit_env_var_takes_precedence(self):
        allowed_sub = os.path.join(_LOCAL_BASE, "custom")
        with patch.dict(os.environ, {"HERMES_DATA_DIR": allowed_sub}, clear=False):
            assert _base_dir() == os.path.realpath(allowed_sub)

    def test_explicit_env_var_rejects_outside_roots(self):
        with patch.dict(os.environ, {"HERMES_DATA_DIR": "/tmp/evil"}, clear=False):
            with pytest.raises(ValueError, match="resolves outside allowed roots"):
                _base_dir()

    def test_docker_path_when_exists(self, tmp_path):
        docker_path = str(tmp_path / "docker_data")
        os.makedirs(docker_path)
        with patch.dict(os.environ, {}, clear=False):
            # Remove HERMES_DATA_DIR if set
            os.environ.pop("HERMES_DATA_DIR", None)
            with patch("infrastructure.paths._DOCKER_BASE", docker_path):
                assert _base_dir() == docker_path

    def test_local_fallback(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HERMES_DATA_DIR", None)
            with patch("infrastructure.paths._DOCKER_BASE", "/nonexistent_docker_path_12345"):
                assert _base_dir() == _LOCAL_BASE


class TestDefaultStructuralDb:
    def test_env_var_override_allowed(self):
        allowed = os.path.join(_LOCAL_BASE, "db.sqlite")
        with patch.dict(os.environ, {"HERMES_STRUCTURAL_DB": allowed}, clear=False):
            assert default_structural_db() == os.path.realpath(allowed)

    def test_env_var_override_rejected(self):
        with patch.dict(os.environ, {"HERMES_STRUCTURAL_DB": "/tmp/evil.db"}, clear=False):
            with pytest.raises(ValueError, match="resolves outside allowed roots"):
                default_structural_db()

    def test_default_uses_base_dir(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HERMES_DATA_DIR", None)
            os.environ.pop("HERMES_STRUCTURAL_DB", None)
            with patch("infrastructure.paths._DOCKER_BASE", "/nonexistent_docker_path_12345"):
                result = default_structural_db()
                assert result == os.path.join(_LOCAL_BASE, "structural", "structure.db")


class TestDefaultSemanticDir:
    def test_env_var_override_allowed(self):
        allowed = os.path.join(_LOCAL_BASE, "chroma")
        with patch.dict(os.environ, {"HERMES_SEMANTIC_DIR": allowed}, clear=False):
            assert default_semantic_dir() == os.path.realpath(allowed)

    def test_env_var_override_rejected(self):
        with patch.dict(os.environ, {"HERMES_SEMANTIC_DIR": "/tmp/evil"}, clear=False):
            with pytest.raises(ValueError, match="resolves outside allowed roots"):
                default_semantic_dir()

    def test_default_uses_base_dir(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HERMES_DATA_DIR", None)
            os.environ.pop("HERMES_SEMANTIC_DIR", None)
            with patch("infrastructure.paths._DOCKER_BASE", "/nonexistent_docker_path_12345"):
                result = default_semantic_dir()
                assert result == os.path.join(_LOCAL_BASE, "semantic", "chroma_db")
