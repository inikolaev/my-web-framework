import asyncio
import time
from typing import Any, cast

from limits import RateLimitItem
from limits.aio import storage, strategies
from limits.aio.strategies import RateLimiter
from limits.storage import storage_from_string
from starlette.requests import Request

from my_web_framework.annotations import Annotation
from my_web_framework.plugins._base import Plugin
from my_web_framework.plugins.rate_limiter.annotations import _LimitAnnotation
from my_web_framework.plugins.rate_limiter.exceptions import RateLimitExceededException, UnsupportedRateLimiterStorage


class RateLimiterPlugin(Plugin):
    def __init__(self, storage_uri: str = "async+memory://") -> None:
        if not storage_uri.startswith("async+"):
            msg = "Only async rate limiter storages are supported"
            raise UnsupportedRateLimiterStorage(
        msg,
        )

        self.__storage = storage_from_string(storage_uri)
        self.__rate_limiter = strategies.MovingWindowRateLimiter(self.__storage)

        self.__fallback_storage = storage.MemoryStorage()
        self.__fallback_rate_limiter = strategies.MovingWindowRateLimiter(
            self.__fallback_storage,
        )

    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, _LimitAnnotation)

    def _evaluate_key_func(
            self, annotation: _LimitAnnotation, request: Request, kwargs: dict[str, Any],
    ) -> str:
        kwargs = {
            name: value
            for name, value in kwargs.items()
            if name in annotation.parameters()
        }
        key_func = annotation.key()

        if annotation.has_request_parameter():
            return key_func(request=request, **kwargs)
        else:
            return key_func(**kwargs)

    async def _evaluate_limit(
            self, limit: RateLimitItem, key: str,
    ) -> tuple[RateLimitItem, str, bool]:
        return limit, key, await self._limiter.hit(limit, key)

    def _collect_limits(
            self, annotation: _LimitAnnotation, request: Request, kwargs: dict[str, Any],
    ) -> list[tuple[RateLimitItem, str]]:
        key = self._evaluate_key_func(annotation, request, kwargs)
        return [(limit, key) for limit in annotation.limits()]

    @property
    def _limiter(self) -> RateLimiter:
        # Check if storage is healthy and use fallback storage otherwise
        # TODO: we should not check storage health on each limit check
        if self.__storage.check():
            return self.__rate_limiter

        return self.__fallback_rate_limiter

    async def do_something(
            self, annotations: list[Annotation], request: Request, **kwargs: Any,
    ):
        anns = cast(list[_LimitAnnotation], annotations)

        # Collect all rate limits
        limits = []
        for annotation in anns:
            limits.extend(self._collect_limits(annotation, request, kwargs))

        # Collect rate limit policy
        policy = ", ".join(
            [f"{limit.amount};w={limit.get_expiry()}" for limit, _ in limits],
        )

        # Check all rate limits concurrently
        results = await asyncio.gather(
            *[self._evaluate_limit(limit, key) for limit, key in limits],
        )

        failed_rate_limit = None
        failed_rate_limit_stats = None

        # Check rate limiting results
        for limit, key, result in results:
            if not result and not failed_rate_limit:
                stats = await self._limiter.get_window_stats(limit, key)
                failed_rate_limit = limit
                failed_rate_limit_stats = stats

        if failed_rate_limit:
            reset_time = int(failed_rate_limit_stats.reset_time - time.time()) + 1
            raise RateLimitExceededException(
                reset_time=reset_time,
                limit=failed_rate_limit.amount,
                policy=policy,
            )

        print(f"RateLimiterPlugin is being called: {annotations}, {request}, {kwargs}")
