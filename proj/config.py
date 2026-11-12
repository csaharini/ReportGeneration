"""Minimal local environment-file loader used for development.

The hosting environment remains the source of truth: values already present in
the process environment always take precedence over `.env`.
"""
import os
from pathlib import Path


def load_local_env():
    path = Path(__file__).with_name(".env")
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ[key] = value


load_local_env()
