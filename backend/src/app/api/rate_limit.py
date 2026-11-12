"""Rate limiting as a FastAPI dependency, built on the `limits` library.

Limits are read from Settings per app instance, and counters live in the configured storage
(Redis in Docker, so every API replica shares the same counters; memory in tests).
"""

import math
import time
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from limits import RateLimitItem, parse
from limits.storage import storage_from_string
from limits.strategies import MovingWindowRateLimiter

from app.config import Settings


class RateLimiter:
    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.rate_limit_enabled
        self._strategy = MovingWindowRateLimiter(
            storage_from_string(settings.rate_limit_storage_uri)
        )
        self._limits: dict[str, RateLimitItem] = {
            "default": parse(settings.rate_limit_default),
            "login": parse(settings.rate_limit_login),
        }

    def check(self, scope: str, client_key: str) -> None:
        """Count one hit; raise 429 with Retry-After when the scope's limit is exceeded."""
        if not self.enabled:
            return
        item = self._limits[scope]
        if self._strategy.hit(item, scope, client_key):
            return
        reset_at = self._strategy.get_window_stats(item, scope, client_key).reset_time
        retry_after = max(1, math.ceil(reset_at - time.time()))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


def client_key(request: Request) -> str:
    # Behind nginx, uvicorn's --proxy-headers makes request.client the real client IP.
    return request.client.host if request.client else "unknown"


def rate_limit(scope: str) -> Callable[[Request], None]:
    def dependency(request: Request) -> None:
        limiter: RateLimiter = request.app.state.rate_limiter
        limiter.check(scope, client_key(request))

    return dependency
