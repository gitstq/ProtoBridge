"""
Built-in middleware implementations for ProtoBridge.

Provides common middleware: authentication, rate limiting, logging,
caching, CORS, request/response logging, and retry logic.
"""

import hashlib
import json
import time
import threading
from collections import OrderedDict
from typing import Dict, List, Optional, Any, Callable

from ..core.server import RequestContext, ResponseContext


class CorsMiddleware:
    """Cross-Origin Resource Sharing (CORS) middleware."""

    def __init__(self, allowed_origins: List[str] = None,
                 allowed_methods: List[str] = None,
                 allowed_headers: List[str] = None,
                 max_age: int = 86400,
                 allow_credentials: bool = False):
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or [
            "GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"
        ]
        self.allowed_headers = allowed_headers or [
            "Content-Type", "Authorization", "X-Requested-With"
        ]
        self.max_age = max_age
        self.allow_credentials = allow_credentials

    def __call__(self, ctx: RequestContext,
                 next_handler: Callable) -> ResponseContext:
        origin = ctx.get_header("origin", "*")

        # Handle preflight
        if ctx.method == "OPTIONS":
            headers = {
                "access-control-allow-origin": origin if origin in self.allowed_origins or "*" in self.allowed_origins else self.allowed_origins[0],
                "access-control-allow-methods": ", ".join(self.allowed_methods),
                "access-control-allow-headers": ", ".join(self.allowed_headers),
                "access-control-max-age": str(self.max_age),
            }
            if self.allow_credentials:
                headers["access-control-allow-credentials"] = "true"
            return ResponseContext(204, b"", headers)

        response = next_handler(ctx)

        response.headers["access-control-allow-origin"] = (
            origin if origin in self.allowed_origins or "*" in self.allowed_origins
            else self.allowed_origins[0]
        )
        response.headers["access-control-allow-methods"] = ", ".join(self.allowed_methods)
        response.headers["access-control-allow-headers"] = ", ".join(self.allowed_headers)
        if self.allow_credentials:
            response.headers["access-control-allow-credentials"] = "true"

        return response


class RateLimitMiddleware:
    """Token bucket rate limiting middleware."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60,
                 by_ip: bool = True, by_header: str = ""):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.by_ip = by_ip
        self.by_header = by_header
        self._buckets: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def _get_key(self, ctx: RequestContext) -> str:
        """Get rate limit key from request context."""
        if self.by_header:
            return ctx.get_header(self.by_header, "anonymous")
        if self.by_ip:
            return ctx.client_address[0]
        return "global"

    def _is_allowed(self, key: str) -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = []
            # Clean old entries
            self._buckets[key] = [
                t for t in self._buckets[key]
                if now - t < self.window_seconds
            ]
            if len(self._buckets[key]) >= self.max_requests:
                return False
            self._buckets[key].append(now)
            return True

    def _cleanup_old_buckets(self):
        """Periodically clean up old bucket entries."""
        now = time.time()
        with self._lock:
            expired = [
                key for key, times in self._buckets.items()
                if not times or now - times[-1] > self.window_seconds * 2
            ]
            for key in expired:
                del self._buckets[key]

    def __call__(self, ctx: RequestContext,
                 next_handler: Callable) -> ResponseContext:
        key = self._get_key(ctx)

        # Periodic cleanup
        if hash(key) % 100 == 0:
            self._cleanup_old_buckets()

        if not self._is_allowed(key):
            return ResponseContext.json(
                {
                    "error": "Rate limit exceeded",
                    "limit": self.max_requests,
                    "window": self.window_seconds,
                },
                429
            )

        response = next_handler(ctx)
        remaining = self.max_requests - len(self._buckets.get(key, []))
        response.headers["x-ratelimit-limit"] = str(self.max_requests)
        response.headers["x-ratelimit-remaining"] = str(max(0, remaining))
        response.headers["x-ratelimit-window"] = str(self.window_seconds)

        return response


class LoggingMiddleware:
    """Request/response logging middleware."""

    def __init__(self, log_body: bool = False, max_body_length: int = 1000):
        self.log_body = log_body
        self.max_body_length = max_body_length
        self.logs: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def __call__(self, ctx: RequestContext,
                 next_handler: Callable) -> ResponseContext:
        start = time.time()

        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": ctx.method,
            "path": ctx.path,
            "client": ctx.client_address[0],
        }

        if self.log_body and ctx.body:
            body_str = ctx.body[:self.max_body_length].decode("utf-8", errors="replace")
            log_entry["request_body"] = body_str

        response = next_handler(ctx)

        elapsed = time.time() - start
        log_entry["status"] = response.status_code
        log_entry["elapsed_ms"] = round(elapsed * 1000, 2)

        with self._lock:
            self.logs.append(log_entry)
            # Keep last 1000 entries
            if len(self.logs) > 1000:
                self.logs = self.logs[-1000:]

        status_color = "✅" if response.status_code < 400 else "⚠️" if response.status_code < 500 else "❌"
        print(f"  {status_color} {ctx.method} {ctx.path} → {response.status_code} ({elapsed*1000:.1f}ms)")

        return response

    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent log entries."""
        with self._lock:
            return list(self.logs[-limit:])

    def clear_logs(self):
        """Clear all log entries."""
        with self._lock:
            self.logs.clear()


class CacheMiddleware:
    """In-memory response caching middleware."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[ResponseContext, float]] = OrderedDict()
        self._lock = threading.Lock()

    def _make_key(self, ctx: RequestContext) -> str:
        """Create cache key from request."""
        key_parts = [ctx.method, ctx.path]
        if ctx.body:
            key_parts.append(hashlib.md5(ctx.body).hexdigest())
        if ctx.query_params:
            sorted_params = sorted(ctx.query_params.items())
            key_parts.append(str(sorted_params))
        return "|".join(key_parts)

    def __call__(self, ctx: RequestContext,
                 next_handler: Callable) -> ResponseContext:
        # Skip caching for non-GET requests
        if ctx.method != "GET":
            return next_handler(ctx)

        cache_key = self._make_key(ctx)

        # Check cache
        with self._lock:
            if cache_key in self._cache:
                response, cached_at = self._cache[cache_key]
                if time.time() - cached_at < self.default_ttl:
                    response.headers["x-cache"] = "HIT"
                    return response
                else:
                    del self._cache[cache_key]

        response = next_handler(ctx)

        # Cache successful responses
        if response.status_code < 400:
            with self._lock:
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
                self._cache[cache_key] = (response, time.time())

        response.headers["x-cache"] = "MISS"
        return response

    def clear_cache(self):
        """Clear all cached responses."""
        with self._lock:
            self._cache.clear()

    def cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._lock:
            return {"size": len(self._cache), "max_size": self.max_size}


class AuthMiddleware:
    """Simple API key / Bearer token authentication middleware."""

    def __init__(self, api_keys: Optional[List[str]] = None,
                 bearer_tokens: Optional[List[str]] = None,
                 header_name: str = "authorization",
                 realm: str = "ProtoBridge"):
        self.api_keys = set(api_keys or [])
        self.bearer_tokens = set(bearer_tokens or [])
        self.header_name = header_name
        self.realm = realm

    def __call__(self, ctx: RequestContext,
                 next_handler: Callable) -> ResponseContext:
        auth_value = ctx.get_header(self.header_name)

        if not auth_value:
            resp = ResponseContext.json(
                {"error": "Authentication required"},
                401,
            )
            resp.headers["www-authenticate"] = f'Bearer realm="{self.realm}"'
            return resp

        # Check Bearer token
        if auth_value.lower().startswith("bearer "):
            token = auth_value[7:]
            if not self.bearer_tokens or token in self.bearer_tokens:
                return next_handler(ctx)

        # Check API key
        if auth_value.lower().startswith("key ") or auth_value.lower().startswith("apikey "):
            key = auth_value.split(" ", 1)[1]
            if not self.api_keys or key in self.api_keys:
                return next_handler(ctx)

        # Direct key match
        if auth_value in self.api_keys or auth_value in self.bearer_tokens:
            return next_handler(ctx)

        return ResponseContext.json(
            {"error": "Invalid authentication credentials"},
            403
        )


class RetryMiddleware:
    """Retry middleware for upstream proxy requests."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0,
                 retry_on_status: List[int] = None):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_on_status = retry_on_status or [502, 503, 504]

    def __call__(self, ctx: RequestContext,
                 next_handler: Callable) -> ResponseContext:
        last_response = None
        for attempt in range(self.max_retries + 1):
            response = next_handler(ctx)
            last_response = response
            if response.status_code not in self.retry_on_status:
                break
            if attempt < self.max_retries:
                time.sleep(self.retry_delay * (attempt + 1))

        if last_response:
            last_response.headers["x-retry-count"] = str(min(attempt, self.max_retries))
        return last_response
