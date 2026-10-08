"""Resolve Data API artifact logical keys to filesystem paths (shares now, cloud later)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from alab_management.config import AlabOSConfig

CONFIG_SECTION = "data_api"
STORAGE_KEY = "storage"


def storage_backends() -> dict[str, dict[str, Any]]:
    """Named storage backends from ``[data_api.storage.<name>]``."""
    try:
        section = AlabOSConfig().get(CONFIG_SECTION) or {}
    except FileNotFoundError:
        return {}
    storage = section.get(STORAGE_KEY) or {}
    return {
        name: dict(cfg)
        for name, cfg in storage.items()
        if isinstance(cfg, Mapping)
    }


def resolve_logical_key(logical_key: str) -> Path:
    """Map ``prefix:relative/path`` (or bare relative path under a single backend) to a local Path.

    Raises ``ValueError`` when the key cannot be resolved or escapes the storage root.
    """
    if not isinstance(logical_key, str) or not logical_key.strip():
        raise ValueError("logical_key must be a non-empty string")

    backends = storage_backends()
    if not backends:
        raise ValueError(
            f"no storage backends configured under [{CONFIG_SECTION}.{STORAGE_KEY}]"
        )

    prefix: str | None = None
    relative: str
    if ":" in logical_key:
        prefix, relative = logical_key.split(":", 1)
    else:
        if len(backends) == 1:
            prefix = next(iter(backends))
            relative = logical_key
        else:
            raise ValueError(
                f"logical_key {logical_key!r} needs a storage prefix "
                f"(one of {sorted(backends)})"
            )

    cfg = backends.get(prefix or "")
    if cfg is None:
        raise ValueError(
            f"unknown storage prefix {prefix!r}; configured: {sorted(backends)}"
        )

    backend = cfg.get("backend") or "filesystem"
    if backend != "filesystem":
        raise ValueError(
            f"storage backend {backend!r} is not implemented yet "
            f"(configure filesystem roots for now; cloud is a placeholder)"
        )

    root = cfg.get("root")
    if not isinstance(root, str) or not root.strip():
        raise ValueError(f"storage {prefix!r} declares no filesystem 'root'")

    root_path = Path(root).resolve()
    # Reject absolute / parent escapes in the relative part.
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"logical_key relative path is not safe: {relative!r}")

    resolved = (root_path / rel).resolve()
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise ValueError(
            f"logical_key resolves outside storage root {root_path}"
        ) from exc
    return resolved


def make_logical_key(storage_name: str, relative_path: str) -> str:
    """Build ``prefix:relative`` using the configured ``logical_prefix`` or the storage name."""
    backends = storage_backends()
    cfg = backends.get(storage_name) or {}
    prefix = cfg.get("logical_prefix") or storage_name
    relative_path = relative_path.replace("\\", "/").lstrip("/")
    return f"{prefix}:{relative_path}"
