import json
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


def cache_path(key: str) -> Path:
    safe = "".join(ch if ch.isalnum() else "_" for ch in key.lower())
    return CACHE_DIR / f"{safe}.json"


def read_cache(key: str, ttl_seconds: int):
    p = cache_path(key)
    if not p.exists():
        return None
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
        age = time.time() - payload.get("_cached_at", 0)
        if age > ttl_seconds:
            return None
        return payload.get("data")
    except Exception:
        return None


def write_cache(key: str, data):
    p = cache_path(key)
    payload = {"_cached_at": time.time(), "data": data}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
