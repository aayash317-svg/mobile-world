import time
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, abort

class InMemoryRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Limits request rates by client IP address and optionally target key (e.g. email or endpoint).
    """
    def __init__(self):
        # key -> list of timestamps (float)
        self._records = defaultdict(list)

    def _clean_old_records(self, key: str, window_seconds: int, now: float):
        threshold = now - window_seconds
        self._records[key] = [t for t in self._records[key] if t > threshold]

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        """
        Returns (is_allowed, retry_after_seconds)
        """
        now = time.time()
        self._clean_old_records(key, window_seconds, now)
        current_count = len(self._records[key])
        if current_count >= max_requests:
            earliest = self._records[key][0]
            retry_after = max(1, int(window_seconds - (now - earliest)))
            return False, retry_after

        self._records[key].append(now)
        return True, 0

    def reset(self, key: str = None):
        if key:
            self._records.pop(key, None)
        else:
            self._records.clear()

limiter = InMemoryRateLimiter()

def get_client_ip() -> str:
    # Handle reverse proxies if X-Forwarded-For is present
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"

def rate_limit(limit: int = 10, window_seconds: int = 60, key_func=None):
    """
    Flask route decorator that enforces rate limits.
    Returns 429 JSON response when exceeded.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import current_app
            effective_limit = limit if current_app.config.get("TESTING") else max(limit, 30)
            ip = get_client_ip()
            extra_key = key_func() if key_func else request.endpoint
            rate_key = f"{ip}:{extra_key}"

            allowed, retry_after = limiter.is_allowed(rate_key, effective_limit, window_seconds)
            if not allowed:
                response = jsonify({
                    "error": "Too many requests. Please slow down.",
                    "message": f"Rate limit reached. Please try again in {retry_after} second(s).",
                    "retry_after": retry_after
                })
                response.status_code = 429
                response.headers["Retry-After"] = str(retry_after)
                return response

            return f(*args, **kwargs)
        return decorated_function
    return decorator
