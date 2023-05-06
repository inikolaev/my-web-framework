import asyncio
import inspect
import json
import time
from typing import Any, Callable, cast

from limits import parse_many, RateLimitItem
from limits.aio import storage, strategies
from limits.aio.strategies import RateLimiter
from limits.storage import storage_from_string
from starlette.requests import Request

from my_web_framework.annotations import Annotation, add_annotation
from my_web_framework.exceptions import HttpException
from my_web_framework.plugins._base import Plugin


class LimitAnnotation(Annotation):
    def __init__(self, expression: str, key: Callable, parameters: set[str]):
        self.__expression = expression
        self.__limits = parse_many(expression)
        self.__key = key
        self.__parameters = frozenset(parameters.copy())
        self.__has_request_parameter = "request" in self.__parameters

    def __str__(self):
        return f"LimitAnnotation(expression={self.__expression}, parameters={self.__parameters})"

    def __repr__(self):
        return f"LimitAnnotation(expression={self.__expression}, parameters={self.__parameters})"

    def key(self) -> Callable:
        return self.__key

    def parameters(self) -> frozenset[str]:
        return self.__parameters

    def has_request_parameter(self) -> bool:
        return self.__has_request_parameter

    def limits(self) -> list[RateLimitItem]:
        return self.__limits


class RateLimitExceededException(HttpException):
    def __init__(self, reset_time: int, limit: int, policy: str):
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
            content=json.dumps({
                "type": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429",
                "title": "Too many requests",
                "status": 429,
                "detail": "Rate-limit policy exceeded",
            }),
        )


class UnsupportedRateLimiterStorage(Exception):
    pass


class RateLimiterPlugin(Plugin):
    def __init__(self, storage_uri: str = "async+memory://") -> None:
        if not storage_uri.startswith("async+"):
            raise UnsupportedRateLimiterStorage("Only async rate limiter storages are supported")

        self.__storage = storage_from_string(storage_uri)
        self.__rate_limiter = strategies.MovingWindowRateLimiter(self.__storage)

        self.__fallback_storage = storage.MemoryStorage()
        self.__fallback_rate_limiter = strategies.MovingWindowRateLimiter(self.__fallback_storage)

    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, LimitAnnotation)

    def _evaluate_key_func(self, annotation: LimitAnnotation, request: Request, kwargs: dict[str, Any]) -> str:
        kwargs = {name: value for name, value in kwargs.items() if name in annotation.parameters()}
        key_func = annotation.key()

        if annotation.has_request_parameter():
            return key_func(request=request, **kwargs)
        else:
            return key_func(**kwargs)

    async def _evaluate_limit(self, limit: RateLimitItem, key: str) -> tuple[RateLimitItem, str, bool]:
        return limit, key, await self._limiter.hit(limit, key)

    def _collect_limits(self, annotation: LimitAnnotation, request: Request, kwargs: dict[str, Any]) -> tuple[RateLimitItem, str]:
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
            self, annotations: list[Annotation], request: Request, **kwargs: Any
    ):
        anns = cast(list[LimitAnnotation], annotations)

        # Collect all rate limits
        limits = []
        for annotation in anns:
            limits.extend(self._collect_limits(annotation, request, kwargs))

        # Collect rate limit policy
        policy = ", ".join([f"{limit.amount};w={limit.get_expiry()}" for limit, _ in limits])

        # Check all rate limits concurrently
        results = await asyncio.gather(*[self._evaluate_limit(limit, key) for limit, key in limits])

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


def limit(expression: str, key: Callable):
    def marker(method: Callable) -> Callable:
        key_parameters = {
            name
            for name, value in inspect.signature(key).parameters.items()
            if name != "self"
        }
        key_parameters_without_request = {
            name for name in key_parameters if name != "request"
        }
        method_parameters = {
            name
            for name, value in inspect.signature(method).parameters.items()
            if name != "self"
        }

        if not key_parameters_without_request.issubset(method_parameters):
            raise ValueError(
                f"Key function `{key.__qualname__}` expects parameters not present in handler `{method.__qualname__}`: {key_parameters_without_request.difference(method_parameters)}"
            )

        add_annotation(method, LimitAnnotation(expression, key, key_parameters))
        return method

    return marker
