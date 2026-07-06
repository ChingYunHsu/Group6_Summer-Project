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

# Resolve redis at import time, but degrade gracefully when the package is
# absent so that importing this module (and thus collecting unit tests) never
# crashes in an environment without Redis installed. _get_client() raises a
# clear RuntimeError if a caller actually tries to use the blacklist without
# redis available.
try:
    import redis as _redis
except ModuleNotFoundError:
    _redis = None

_KEY_PREFIX = "auth:blacklist:"


def _get_client():
    global _client
    if _client is None:
        if _redis is None:
            raise RuntimeError(
                "redis is required for the token blacklist. "
                "Install backend dependencies before using auth endpoints."
            )
        _client = _redis.Redis.from_url(
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
    except (_redis.RedisError if _redis else RuntimeError):
        logger.warning("Could not reach Redis to blacklist token; logout may not propagate.")


def is_blacklisted(token: str) -> bool:
    """Check whether a token's signature has been revoked via logout."""
    key = _KEY_PREFIX + _signature_of(token)
    try:
        return bool(_get_client().exists(key))
    except (_redis.RedisError if _redis else RuntimeError):
        logger.warning("Could not reach Redis to check token blacklist; failing open.")
        return False
