import json
import os
import hashlib
from typing import Any, Optional

class StagingBuffer:
    """
    Intermediate Staging Buffer for caching expensive operations results.
    Zero-Fat implementation.
    """
    CACHE_DIR = ".cache/staging_buffer"

    @classmethod
    def get(cls, key: str, params: Any) -> Optional[Any]:
        cache_key = cls._make_key(key, params)
        path = os.path.join(cls.CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    @classmethod
    def set(cls, key: str, params: Any, result: Any) -> None:
        if not os.path.exists(cls.CACHE_DIR):
            os.makedirs(cls.CACHE_DIR, exist_ok=True)
        cache_key = cls._make_key(key, params)
        path = os.path.join(cls.CACHE_DIR, f"{cache_key}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)

    @classmethod
    def _make_key(cls, key: str, params: Any) -> str:
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(f"{key}:{param_str}".encode("utf-8")).hexdigest()

    PENDING_EVOLUTION_PATH = "ontology/pending_evolution.json"

    @classmethod
    def get_pending_evolution(cls) -> list[Any]:
        path = cls.PENDING_EVOLUTION_PATH
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    @classmethod
    def save_pending_evolution(cls, data: list[Any]) -> None:
        path = cls.PENDING_EVOLUTION_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


