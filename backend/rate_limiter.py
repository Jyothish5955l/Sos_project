"""
SOS Guardian - Sliding-Window Thread-Safe Rate Limiter
Provides rate-limiting protection against brute-force, DoS, and spam attacks.
"""

import time
from collections import defaultdict
from threading import Lock


class RateLimiter:
    """
    In-memory thread-safe sliding window rate limiter.
    Does not require external dependencies or Redis.
    """

    def __init__(self):
        self._records = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        """
        Check if a request under `key` is allowed within `window_seconds`.
        Returns (is_allowed: bool, retry_after_seconds: int).
        """
        now = time.time()
        with self._lock:
            timestamps = self._records[key]

            # Retain only timestamps within the rolling window
            valid_timestamps = [t for t in timestamps if (now - t) < window_seconds]

            if len(valid_timestamps) >= max_requests:
                # Calculate remaining wait time based on oldest valid attempt
                oldest = valid_timestamps[0]
                retry_after = max(1, int(window_seconds - (now - oldest)) + 1)
                self._records[key] = valid_timestamps
                return False, retry_after

            # Allow request and append current timestamp
            valid_timestamps.append(now)
            self._records[key] = valid_timestamps
            return True, 0

    def reset(self, key: str):
        """Reset recorded attempts for a specific key (e.g. on successful login)."""
        with self._lock:
            if key in self._records:
                del self._records[key]

    def clear_all(self):
        """Clear all rate limit records (useful for test suites)."""
        with self._lock:
            self._records.clear()


rate_limiter = RateLimiter()
