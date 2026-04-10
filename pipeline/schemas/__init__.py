"""JSON schema loader for pipeline stages."""

from __future__ import annotations

import json
from pathlib import Path

_SCHEMA_DIR = Path(__file__).resolve().parent


def load_schema(name: str) -> dict:
    """Load and return a JSON schema by name (without .json extension)."""
    path = _SCHEMA_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
