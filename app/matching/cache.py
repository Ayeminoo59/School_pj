"""
In-memory match result cache (Weeks 15-16 performance task).

The cache is versioned: whenever a user's modules, availability or account
data changes, `invalidate()` bumps the global version and clears the store.
This prevents recomputing the O(n²) pair comparison on every page view and
keeps results fresh.
"""
import threading
import time


class MatchCache:
    def __init__(self, ttl_seconds: int = 300):
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._store = {}
        self._version = 0

    def invalidate(self) -> None:
        """Bump the version — all previously cached results become stale."""
        with self._lock:
            self._version += 1
            self._store.clear()

    def get(self, user_id: int):
        with self._lock:
            entry = self._store.get(user_id)
            if entry is None:
                return None
            version, created_at, data = entry
            if version != self._version or (time.time() - created_at) > self._ttl:
                # stale (data changed or TTL expired)
                del self._store[user_id]
                return None
            return data

    def set(self, user_id: int, data) -> None:
        with self._lock:
            self._store[user_id] = (self._version, time.time(), data)
