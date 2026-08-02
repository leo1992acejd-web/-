"""HTTPレスポンス用のシンプルなファイルキャッシュ。

--force-refresh 指定時は呼び出し側 (crawler.py) が読み込みをスキップする。
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Optional

from loguru import logger


class HttpCache:
    def __init__(self, cache_dir: Path, ttl_seconds: int, enabled: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.enabled = enabled

    def _paths(self, key: str) -> tuple[Path, Path]:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.data", self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> Optional[str]:
        if not self.enabled:
            return None
        data_path, meta_path = self._paths(key)
        if not data_path.exists() or not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if time.time() - meta.get("fetched_at", 0) > self.ttl_seconds:
            return None
        try:
            return data_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def set(self, key: str, content: str) -> None:
        if not self.enabled:
            return
        data_path, meta_path = self._paths(key)
        try:
            data_path.write_text(content, encoding="utf-8")
            meta_path.write_text(
                json.dumps({"key": key, "fetched_at": time.time()}), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning(f"Failed to write cache for {key}: {exc}")

    def clear(self) -> None:
        for path in self.cache_dir.glob("*"):
            try:
                path.unlink()
            except OSError:
                pass
