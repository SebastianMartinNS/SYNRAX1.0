import json
import redis
import logging
from typing import Any, Optional
from src.config import Config

logger = logging.getLogger(__name__)

class CacheManager:
    """Redis-based caching manager"""

    def __init__(self, config: Config):
        self.config = config
        self.redis_client = None

        if self.config.cache_enabled:
            try:
                self.redis_client = redis.from_url(self.config.redis_url)
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, caching disabled: {str(e)}")
                self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.redis_client:
            return False

        try:
            ttl = ttl or self.config.cache_ttl
            serialized_value = json.dumps(value)
            return bool(self.redis_client.setex(key, ttl, serialized_value))
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis_client:
            return False

        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error: {str(e)}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error: {str(e)}")
            return 0

# Cache key generators
def get_query_cache_key(question: str, user_id: int) -> str:
    """Generate cache key for query results"""
    # Simple hash of question + user_id to avoid key length issues
    import hashlib
    key_content = f"{user_id}:{question[:100]}"
    return f"query:{hashlib.md5(key_content.encode()).hexdigest()}"

def get_session_cache_key(session_id: str) -> str:
    """Generate cache key for sessions"""
    return f"session:{session_id}"

def get_report_cache_key() -> str:
    """Generate cache key for security reports"""
    return "security_report"