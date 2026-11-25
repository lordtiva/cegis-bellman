"""
Versioned Certificate Archive Schema (.json.xz) with SHA-256 Integrity Check.
"""

from __future__ import annotations

import hashlib
import json
import lzma
import os
import time
from typing import Any, Dict


SCHEMA_VERSION = "1.0"


def _canonical_json_bytes(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_payload_sha256(models_dict: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(models_dict)).hexdigest()


def save_certificate_archive(
    path: str,
    models_dict: Dict[str, Any],
    metadata: Dict[str, Any] | None = None,
) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    digest = compute_payload_sha256(models_dict)
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sha256_models": digest,
        "metadata": metadata or {},
        "models": models_dict,
    }
    raw = json.dumps(envelope, indent=None, separators=(",", ":")).encode("utf-8")
    with lzma.open(path, "wb", preset=6) as fh:
        fh.write(raw)
    return digest


def load_certificate_archive(path: str, verify_hash: bool = True) -> Dict[str, Any]:
    with lzma.open(path, "rb") as fh:
        envelope = json.loads(fh.read().decode("utf-8"))
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema_version: {envelope.get('schema_version')}")
    if verify_hash:
        expected = envelope.get("sha256_models", "")
        actual = compute_payload_sha256(envelope["models"])
        if actual != expected:
            raise ValueError(f"SHA-256 mismatch: expected {expected}, got {actual}")
    return envelope
