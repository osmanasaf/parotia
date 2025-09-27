import json
import zlib
from typing import Optional, Any
import redis
from .config import get_settings


class CacheService:
    """Basit Redis cache servisi (JSON + opsiyonel zlib)"""

    def __init__(self, url: Optional[str] = None, compress: bool = True):
        settings = get_settings()
        self.redis = redis.Redis.from_url(url or settings.REDIS_URL, decode_responses=False)
        self.compress = compress

    def get_json(self, key: str) -> Optional[Any]:
        try:
            data = self.redis.get(key)
        except Exception:
            return None
        if data is None:
            return None
        if self.compress:
            try:
                data = zlib.decompress(data)
            except zlib.error:
                pass
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return json.loads(data)
        except Exception:
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int) -> bool:
        try:
            raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
            payload = zlib.compress(raw) if self.compress else raw
            try:
                self.redis.setex(key, ttl_seconds, payload)
            except Exception:
                return False
            return True
        except Exception:
            return False

    def delete(self, key: str) -> int:
        try:
            return int(self.redis.delete(key))
        except Exception:
            return 0

    def delete_by_pattern(self, pattern: str) -> int:
        deleted = 0
        try:
            for k in self.redis.scan_iter(pattern):
                deleted += int(self.redis.delete(k))
        except Exception:
            pass
        return deleted


