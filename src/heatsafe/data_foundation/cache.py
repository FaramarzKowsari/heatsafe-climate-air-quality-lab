from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def canonical_request_key(namespace: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"namespace": namespace, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class JsonDiskCache:
    def __init__(self, root: str | Path | None = None) -> None:
        configured = root or os.getenv("HEATSAFE_CACHE_DIR") or Path.home() / ".cache" / "heatsafe"
        self.root = Path(configured)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            expires_at = datetime.fromisoformat(str(record["expires_at"]))
            if expires_at <= datetime.now(UTC):
                path.unlink(missing_ok=True)
                return None
            payload = record.get("payload")
            return payload if isinstance(payload, dict) else None
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            return None

    def set(self, key: str, payload: dict[str, Any], ttl: timedelta) -> Path:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + ttl).isoformat(),
            "payload": payload,
        }
        encoded = json.dumps(record, sort_keys=True, ensure_ascii=False)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            stream.write(encoded)
            temporary = Path(stream.name)
        temporary.replace(path)
        return path

    def delete(self, key: str) -> bool:
        path = self._path(key)
        existed = path.exists()
        path.unlink(missing_ok=True)
        return existed

    def purge_expired(self) -> int:
        removed = 0
        for path in self.root.rglob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                expires_at = datetime.fromisoformat(str(record["expires_at"]))
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                path.unlink(missing_ok=True)
                removed += 1
                continue
            if expires_at <= datetime.now(UTC):
                path.unlink(missing_ok=True)
                removed += 1
        return removed
