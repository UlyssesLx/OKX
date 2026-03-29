"""
API缓存模块
减少不必要的API调用，提升性能
"""
from typing import Dict, Any, Optional, Callable, Generic, TypeVar
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import hashlib
import json
import asyncio


T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    value: T
    created_at: datetime
    expires_at: Optional[datetime] = None
    hit_count: int = 0
    last_accessed: datetime = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def access(self) -> T:
        self.hit_count += 1
        self.last_accessed = datetime.now()
        return self.value


class APICache:
    """
    API响应缓存
    支持TTL过期、LRU淘汰、统计信息
    """
    _instance: Optional['APICache'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size: int = 1000
        self._default_ttl: int = 300
        self._total_hits: int = 0
        self._total_misses: int = 0

    def configure(self, max_size: int = 1000, default_ttl: int = 300):
        """配置缓存参数"""
        self._max_size = max_size
        self._default_ttl = default_ttl

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [prefix]
        for arg in args:
            key_parts.append(str(arg))
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self._cache:
            self._total_misses += 1
            return None

        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            self._total_misses += 1
            return None

        self._total_hits += 1
        return entry.access()

    def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存值"""
        if ttl is None:
            ttl = self._default_ttl

        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None

        self._cache[key] = CacheEntry(
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            hit_count=0,
            last_accessed=datetime.now()
        )

        if len(self._cache) > self._max_size:
            self._evict_lru()

    def _evict_lru(self):
        """淘汰最久未使用的缓存"""
        if not self._cache:
            return

        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        del self._cache[lru_key]

    def delete(self, key: str):
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._total_hits = 0
        self._total_misses = 0

    def cleanup_expired(self):
        """清理过期缓存"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._total_hits + self._total_misses
        hit_rate = (self._total_hits / total * 100) if total > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total
        }

    def cached(self, prefix: str, ttl: int = None):
        """装饰器：缓存函数返回值"""
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            async def async_wrapper(*args, **kwargs) -> T:
                key = self._make_key(prefix, *args, **kwargs)
                cached_value = self.get(key)
                if cached_value is not None:
                    return cached_value

                result = await func(*args, **kwargs)
                if result is not None:
                    self.set(key, result, ttl)
                return result

            def sync_wrapper(*args, **kwargs) -> T:
                key = self._make_key(prefix, *args, **kwargs)
                cached_value = self.get(key)
                if cached_value is not None:
                    return cached_value

                result = func(*args, **kwargs)
                if result is not None:
                    self.set(key, result, ttl)
                return result

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator


api_cache = APICache()


def get_api_cache() -> APICache:
    return api_cache


def cached(prefix: str, ttl: int = None):
    """便捷装饰器：缓存函数返回值"""
    return api_cache.cached(prefix, ttl)