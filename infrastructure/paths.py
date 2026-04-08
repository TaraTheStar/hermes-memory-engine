import os

# Base data directory: honour env var, then Docker path, then local fallback.
_DOCKER_BASE = "/data/hermes_memory_engine"
_LOCAL_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".data")

# Allowed root directories for data paths.
_ALLOWED_ROOTS = (
    os.path.realpath(_DOCKER_BASE),
    os.path.realpath(_LOCAL_BASE),
)


def _validate_data_path(path: str) -> str:
    """Resolve the path and verify it falls under an allowed root."""
    resolved = os.path.realpath(path)
    if any(resolved == root or resolved.startswith(root + os.sep) for root in _ALLOWED_ROOTS):
        return resolved
    raise ValueError(f"Data path '{path}' resolves outside allowed roots: {_ALLOWED_ROOTS}")


def _base_dir() -> str:
    explicit = os.environ.get("HERMES_DATA_DIR")
    if explicit:
        return _validate_data_path(explicit)
    if os.path.isdir(_DOCKER_BASE):
        return _DOCKER_BASE
    return _LOCAL_BASE


def default_structural_db() -> str:
    env_val = os.environ.get("HERMES_STRUCTURAL_DB")
    if env_val:
        return _validate_data_path(env_val)
    return os.path.join(_base_dir(), "structural", "structure.db")


def default_semantic_dir() -> str:
    env_val = os.environ.get("HERMES_SEMANTIC_DIR")
    if env_val:
        return _validate_data_path(env_val)
    return os.path.join(_base_dir(), "semantic", "chroma_db")
