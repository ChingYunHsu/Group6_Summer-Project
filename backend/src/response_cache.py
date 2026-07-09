"""Redis-backed, short-TTL cache for expensive read endpoints.

Modeled on token_blacklist.py's Redis pattern: lazy client, graceful
degradation when redis isn't installed/reachable, fail-open on any Redis
error (a cache outage should degrade to "always recompute", never break
the endpoint).
"""

import json
import logging

from settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_client = None

try:
    import redis as _redis
except ModuleNotFoundError:
    _redis = None


def _get_client():
    global _client
    if _client is None:
        if _redis is None:
            raise RuntimeError(
                "redis is required for response_cache. "
                "Install backend dependencies before using cached endpoints."
            )
        _client = _redis.Redis.from_url(
            _settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
    return _client


def get_cached(key: str):
    """Return the cached JSON-decoded value for `key`, or None on a cache
    miss / any Redis error (fail open — caller falls through to a live
    computation)."""
    try:
        raw = _get_client().get(key)
    except (_redis.RedisError if _redis else RuntimeError):
        logger.warning("Could not reach Redis for cache read; treating as a miss.")
        return None

    if raw is None:
        return None

    try:
        return json.loads(raw)
    except ValueError:
        return None


def set_cached(key: str, value, ttl_seconds: int) -> None:
    """Best-effort cache write. Swallows Redis errors — a failed cache
    write must never fail the request it's caching."""
    try:
        _get_client().set(key, json.dumps(value), ex=ttl_seconds)
    except (_redis.RedisError if _redis else RuntimeError):
        logger.warning("Could not reach Redis for cache write; response will not be cached.")
