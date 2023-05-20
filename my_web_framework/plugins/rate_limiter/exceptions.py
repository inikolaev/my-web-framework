import json

from my_web_framework.exceptions import HttpException


class RateLimitExceededException(HttpException):
    def __init__(self, reset_time: int, limit: int, policy: str) -> None:
        super().__init__(
            status_code=429,
            headers={
                "Content-Type": "application/problem+json",
                "Retry-After": str(reset_time),
                # https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/
                "RateLimit-Limit": str(limit),
                "RateLimit-Policy": policy,
                "RateLimit-Reset": str(reset_time),
            },
            content=json.dumps(
                {
                    "type": (
                        "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429"
                    ),
                    "title": "Too many requests",
                    "status": 429,
                    "detail": "Rate-limit policy exceeded",
                },
            ),
        )


class UnsupportedRateLimiterStorage(Exception):
    pass
