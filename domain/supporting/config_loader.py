import yaml
import os
from typing import Dict, Any, Optional
from domain.core.acl.storage_translator import StorageTranslator

DEFAULT_CONFIG_PATH = os.environ.get('HERMES_CONFIG_PATH', '/opt/data/config.yaml')

# Directories the config file is allowed to reside in.
_ALLOWED_ROOTS = (
    "/opt/data",
    "/data",
    "/tmp",
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

        try:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to parse configuration: {e}")

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
