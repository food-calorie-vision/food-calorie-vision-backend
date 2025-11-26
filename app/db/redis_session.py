import logging
import redis.asyncio as redis
from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

redis_client = None
if settings.redis_url:
    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis client initialized with %s", settings.redis_url)
    except Exception as exc:  # pragma: no cover
        logger.warning("Redis connection failed (%s). Continuing without Redis.", exc)
        redis_client = None
else:
    logger.warning("REDIS_URL not configured. Chat session context sharing is disabled.")

def get_redis_client():
    """
    Returns a Redis client instance.
    """
    return redis_client
