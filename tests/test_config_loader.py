import os
import tempfile
import pytest

from domain.supporting.config_loader import ConfigLoader


def test_missing_config_file_raises():
    """Missing config file should raise FileNotFoundError with helpful message."""
    with pytest.raises(FileNotFoundError, match="HERMES_CONFIG_PATH"):
        ConfigLoader("/tmp/hermes_nonexistent_config.yaml")


def test_path_outside_allowlist_raises():
    """Config path outside allowed directories should raise ValueError."""
    with pytest.raises(ValueError, match="outside the allowed directories"):
        ConfigLoader("/nonexistent/path/config.yaml")


def test_valid_config_loads():
    """Valid YAML config should load successfully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("delegation:\n  base_url: http://localhost:8080\n  api_key: test-key\n  model: test-model\n")
        f.flush()
        try:
            loader = ConfigLoader(f.name)
            config = loader.get_delegation_config()
            assert config["base_url"] == "http://localhost:8080"
            assert config["api_key"] == "test-key"
            assert config["model"] == "test-model"
        finally:
            os.unlink(f.name)


def test_missing_delegation_block_raises():
    """Config without delegation block should raise KeyError."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("other_key: value\n")
        f.flush()
        try:
            loader = ConfigLoader(f.name)
            with pytest.raises(KeyError):
                loader.get_delegation_config()
        finally:
            os.unlink(f.name)


def test_invalid_yaml_raises():
    """Malformed YAML should raise RuntimeError."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        # Use content that yaml.safe_load reliably rejects
        f.write("key: [\ninvalid:\n  - {\n")
        f.flush()
        try:
            with pytest.raises(RuntimeError, match="Failed to parse"):
                ConfigLoader(f.name)
        finally:
            os.unlink(f.name)
