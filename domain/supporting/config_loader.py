import yaml
import os
import stat
import logging
from typing import Dict, Any, Optional
from domain.core.acl.storage_translator import StorageTranslator

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.environ.get('HERMES_CONFIG_PATH', '/opt/data/config.yaml')

# Directories the config file is allowed to reside in.
_ALLOWED_ROOTS = (
    "/opt/data",
    "/data",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # project root
)


class ConfigLoader:
    """
    Utility to load system-level configuration files.
    Ensures secrets are read from the environment/config at runtime,
    not hardcoded in the repository.
    """
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = self._validate_path(config_path)
        self._config: Dict[str, Any] = {}
        self.translator = StorageTranslator()
        self._load_config()

    @staticmethod
    def _validate_path(config_path: str) -> str:
        """Resolve and verify the config path is within an allowed directory."""
        resolved = os.path.realpath(config_path)
        if not any(resolved.startswith(os.path.realpath(root) + os.sep) or resolved == os.path.realpath(root)
                   for root in _ALLOWED_ROOTS):
            raise ValueError(
                f"Configuration path '{resolved}' is outside the allowed directories: {_ALLOWED_ROOTS}"
            )
        return resolved

    def _load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"Configuration file not found at {self.config_path}. "
                f"Set the HERMES_CONFIG_PATH environment variable to specify a custom path."
            )

        # Warn if the config file (which may contain API keys) is world-readable
        try:
            file_mode = os.stat(self.config_path).st_mode
            if file_mode & stat.S_IROTH:
                logger.warning(
                    "Config file %s is world-readable (mode %o). "
                    "Consider restricting permissions: chmod 600 %s",
                    self.config_path, file_mode & 0o777, self.config_path
                )
        except OSError:
            pass

        try:
            with open(self.config_path, 'r') as f:
                raw = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to parse configuration: {e}")

        if not isinstance(raw, dict):
            raise RuntimeError(
                f"Configuration file must contain a YAML mapping, got {type(raw).__name__}"
            )
        self._config = raw

    def get_delegation_config(self) -> Dict[str, Any]:
        """
        Retrieve the 'delegation' block containing LLM provider details.
        """
        delegation = self._config.get('delegation')
        if not delegation:
            raise KeyError("Missing 'delegation' configuration in config.yaml")
        return delegation

    def get_all(self) -> Dict[str, Any]:
        return self._config
