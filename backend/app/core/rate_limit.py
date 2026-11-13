"""Rate limiting middleware and utilities for API protection."""
import time
import logging
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter tracking request timestamps per client IP."""

    def __init__(self):
        # Maps client_key -> list of request timestamps (epoch seconds)
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_rate_limited(self, client_key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int, int]:
        """Check if request exceeds quota in current sliding window.
        
        Returns:
            (is_limited, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds

        # Evict timestamps older than the sliding window
        timestamps = [t for t in self._requests[client_key] if t > window_start]
        self._requests[client_key] = timestamps

        if len(timestamps) >= max_requests:
            oldest_in_window = timestamps[0]
            retry_after = int(max(1, oldest_in_window + window_seconds - now))
            return True, 0, retry_after

        # Record this request
        timestamps.append(now)
        remaining = max_requests - len(timestamps)
        return False, remaining, 0


# Global limiter instance
global_rate_limiter = SlidingWindowRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware enforcing path-specific rate limits."""

    EXEMPT_PATHS = {"/health", "/api/v1/health", "/docs", "/redoc", "/api/v1/openapi.json", "/openapi.json"}

    AUTH_LIMIT = 15  # 15 requests per minute for login/register
    DEFAULT_LIMIT = 120  # 120 requests per minute for general API endpoints

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip rate limiting for health and docs
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Identify client (use X-Forwarded-For if behind reverse proxy, else client.host)
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else "127.0.0.1")

        # Determine path quota
        is_prod = settings.ENVIRONMENT == "production" and not settings.DEBUG
        auth_limit = self.AUTH_LIMIT if is_prod else 500
        default_limit = self.DEFAULT_LIMIT if is_prod else 1000

        if "/api/v1/auth" in path:
            max_reqs = auth_limit
            client_key = f"auth:{client_ip}"
        else:
            max_reqs = default_limit
            client_key = f"api:{client_ip}"

        is_limited, remaining, retry_after = global_rate_limiter.is_rate_limited(
            client_key=client_key,
            max_requests=max_reqs,
            window_seconds=60
        )

        if is_limited:
            logger.warning(f"Rate limit exceeded for client {client_ip} on path {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please wait before making further requests.",
                    "retry_after_seconds": retry_after
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_reqs),
                    "X-RateLimit-Remaining": "0"
                }
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_reqs)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
