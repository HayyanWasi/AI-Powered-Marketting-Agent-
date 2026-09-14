from src.cache.cache import SessionCache

# Global cache instance for the application
session_cache = SessionCache()

__all__ = ["SessionCache", "session_cache"]
