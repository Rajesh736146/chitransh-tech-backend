"""Redis cache service using Upstash Redis (TLS-enabled)."""

import json
import logging
from typing import Any

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Redis client singleton ────────────────────────────────────────────────────

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Get or create the Redis client (thread-safe singleton)."""
    global _redis_client
    if _redis_client is None:
        if settings.redis_url:
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        else:
            _redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                ssl=settings.redis_tls,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
    return _redis_client


class RedisService:
    """High-level cache service wrapping Redis operations."""

    def __init__(self):
        self.client = get_redis_client()

    # ─── Basic operations ─────────────────────────────────────────────────────

    def get(self, key: str) -> str | None:
        """Get a string value by key."""
        try:
            return self.client.get(key)
        except redis.RedisError as e:
            logger.warning(f"Redis GET failed for key={key}: {e}")
            return None

    def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """
        Set a string value with optional TTL (seconds).

        Args:
            key: Cache key.
            value: String value to store.
            ttl: Time-to-live in seconds. None = no expiry.
        """
        try:
            self.client.set(key, value, ex=ttl)
            return True
        except redis.RedisError as e:
            logger.warning(f"Redis SET failed for key={key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete a key."""
        try:
            self.client.delete(key)
            return True
        except redis.RedisError as e:
            logger.warning(f"Redis DELETE failed for key={key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        try:
            return bool(self.client.exists(key))
        except redis.RedisError as e:
            logger.warning(f"Redis EXISTS failed for key={key}: {e}")
            return False

    # ─── JSON helpers ─────────────────────────────────────────────────────────

    def get_json(self, key: str) -> Any | None:
        """Get and deserialize a JSON value."""
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_json(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Serialize and store a value as JSON."""
        try:
            return self.set(key, json.dumps(value, default=str), ttl=ttl)
        except (TypeError, ValueError) as e:
            logger.warning(f"Redis SET_JSON serialization failed: {e}")
            return False

    # ─── Counter / rate-limiting helpers ──────────────────────────────────────

    def increment(self, key: str, ttl: int | None = None) -> int:
        """Increment a counter. Sets TTL on first creation."""
        try:
            pipe = self.client.pipeline()
            pipe.incr(key)
            if ttl:
                pipe.expire(key, ttl)
            results = pipe.execute()
            return results[0]
        except redis.RedisError as e:
            logger.warning(f"Redis INCR failed for key={key}: {e}")
            return 0

    def get_ttl(self, key: str) -> int:
        """Get remaining TTL in seconds. -1 = no expiry, -2 = key doesn't exist."""
        try:
            return self.client.ttl(key)
        except redis.RedisError as e:
            logger.warning(f"Redis TTL failed for key={key}: {e}")
            return -2

    # ─── Health check ─────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            return self.client.ping()
        except redis.RedisError as e:
            logger.error(f"Redis PING failed: {e}")
            return False
