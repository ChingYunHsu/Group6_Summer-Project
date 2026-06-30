"""Redis-backed JWT revocation (logout) blacklist.

Keyed by the token's own signature segment (the third dot-separated part of
the JWT), per the logout contract: "append the incoming token signature into
the Redis invalidation blacklist." Entries expire automatically at the
token's own `exp`, so revoked entries never outlive the token they revoke.

The blacklist is a secondary, best-effort revocation layer on top of the
primary defense (JWT signature + expiry verification in auth.py). If Redis
itself is unreachable, is_blacklisted() fails open (logs and returns False)
rather than locking every request out because a side-channel store is down.
"""

import logging
import time

from settings import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()
_client = None

_KEY_PREFIX = "auth:blacklist:"


class _RedisUnavailable(Exception):
    pass


def _get_client():
    global _client
    if _client is None:
        try:
            import redis
        except ModuleNotFoundError as exc:
            raise _RedisUnavailable from exc

        _client = redis.Redis.from_url(
            _settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
    return _client


def _signature_of(token: str) -> str:
    return token.rsplit(".", 1)[-1]


def blacklist_token(token: str, exp: int) -> None:
    """Revoke a token by storing its signature until the token's own exp."""
    ttl_seconds = int(exp - time.time())
    if ttl_seconds <= 0:
        return  # already expired; nothing to revoke

    key = _KEY_PREFIX + _signature_of(token)
    try:
        _get_client().set(key, "1", ex=ttl_seconds)
    except Exception:
        logger.warning("Could not reach Redis to blacklist token; logout may not propagate.")


def is_blacklisted(token: str) -> bool:
    """Check whether a token's signature has been revoked via logout."""
    key = _KEY_PREFIX + _signature_of(token)
    try:
        return bool(_get_client().exists(key))
    except Exception:
        logger.warning("Could not reach Redis to check token blacklist; failing open.")
        return False
