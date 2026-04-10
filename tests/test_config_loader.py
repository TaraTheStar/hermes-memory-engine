import os
import tempfile
import pytest

from domain.supporting.config_loader import ConfigLoader, _ALLOWED_ROOTS


@pytest.fixture
def _config_dir():
    """Create a temp dir inside an allowed root for config tests."""
    # _ALLOWED_ROOTS includes the domain/ directory; use a subdir of it.
    allowed_root = os.path.realpath(_ALLOWED_ROOTS[-1])
    config_dir = os.path.join(allowed_root, ".test_config_tmp")
    os.makedirs(config_dir, exist_ok=True)
    yield config_dir
    import shutil
    shutil.rmtree(config_dir, ignore_errors=True)


def test_missing_config_file_raises(_config_dir):
    """Missing config file should raise FileNotFoundError with helpful message."""
    with pytest.raises(FileNotFoundError, match="HERMES_HOME"):
        ConfigLoader(os.path.join(_config_dir, "nonexistent.yaml"))


def test_path_outside_allowlist_raises():
    """Config path outside allowed directories should raise ValueError."""
    with pytest.raises(ValueError, match="outside the allowed directories"):
        ConfigLoader("/nonexistent/path/config.yaml")


def test_tmp_is_not_in_allowed_roots():
    """/tmp should not be an allowed config root."""
    assert not any(
        os.path.realpath("/tmp").startswith(os.path.realpath(root) + os.sep)
        or os.path.realpath("/tmp") == os.path.realpath(root)
        for root in _ALLOWED_ROOTS
    )


def test_valid_config_loads(_config_dir):
    """Valid YAML config should load successfully."""
    path = os.path.join(_config_dir, "test_config.yaml")
    with open(path, "w") as f:
        f.write("delegation:\n  base_url: http://localhost:8080\n  api_key: test-key\n  model: test-model\n")
    try:
        loader = ConfigLoader(path)
        config = loader.get_delegation_config()
        assert config["base_url"] == "http://localhost:8080"
        assert config["api_key"] == "test-key"
        assert config["model"] == "test-model"
    finally:
        os.unlink(path)


def test_missing_delegation_block_raises(_config_dir):
    """Config without delegation block should raise KeyError."""
    path = os.path.join(_config_dir, "no_delegation.yaml")
    with open(path, "w") as f:
        f.write("other_key: value\n")
    try:
        loader = ConfigLoader(path)
        with pytest.raises(KeyError):
            loader.get_delegation_config()
    finally:
        os.unlink(path)


def test_invalid_yaml_raises(_config_dir):
    """Malformed YAML should raise RuntimeError."""
    path = os.path.join(_config_dir, "bad.yaml")
    with open(path, "w") as f:
        # Use content that yaml.safe_load reliably rejects
        f.write("key: [\ninvalid:\n  - {\n")
    try:
        with pytest.raises(RuntimeError, match="Failed to parse"):
            ConfigLoader(path)
    finally:
        os.unlink(path)


def test_empty_yaml_raises(_config_dir):
    """Empty YAML file (returns None) should raise RuntimeError."""
    path = os.path.join(_config_dir, "empty.yaml")
    with open(path, "w") as f:
        f.write("")
    try:
        with pytest.raises(RuntimeError, match="YAML mapping"):
            ConfigLoader(path)
    finally:
        os.unlink(path)


def test_non_dict_yaml_raises(_config_dir):
    """YAML file with a list root should raise RuntimeError."""
    path = os.path.join(_config_dir, "list.yaml")
    with open(path, "w") as f:
        f.write("- item1\n- item2\n")
    try:
        with pytest.raises(RuntimeError, match="YAML mapping"):
            ConfigLoader(path)
    finally:
        os.unlink(path)
