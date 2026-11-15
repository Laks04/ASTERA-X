import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    """Per-client sliding window; in-process only (use Redis before running several API instances)."""
    def __init__(self, limit: int, window: int = 60):
        self.limit, self.window, self.hits = limit, window, defaultdict(list)

    def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.time()
        self.hits[key] = [t for t in self.hits[key] if now - t < self.window]
        if len(self.hits[key]) >= self.limit:
            raise HTTPException(429, "Too many requests. Try again shortly.")
        self.hits[key].append(now)
