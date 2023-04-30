import inspect
import json
import time
from typing import Any, Callable, cast

from limits import parse, RateLimitItem
from limits.aio import storage, strategies
from starlette.requests import Request

from my_web_framework.annotations import Annotation, add_annotation
from my_web_framework.exceptions import HttpException
from my_web_framework.plugins._base import Plugin


class LimitAnnotation(Annotation):
    def __init__(self, expression: str, key: Callable, parameters: set[str]):
        self.__expression = expression
        self.__limit = parse(expression)
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

    def limit(self) -> RateLimitItem:
        return self.__limit


class RateLimitExceededException(HttpException):
    def __init__(self, reset_time: int, remaining_time: int):
        super().__init__(
            status_code=429,
            headers={
                "Content-Type": "application/problem+json",
                "Retry-After": str(remaining_time),
            },
            content=json.dumps({
                "type": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429",
                "title": "Too many requests",
                "status": 429,
                "detail": "Rate-limit policy exceeded",
            }),
        )


class RateLimiterPlugin(Plugin):
    def __init__(self) -> None:
        self.__storage = storage.MemoryStorage()
        self.__rate_limiter = strategies.MovingWindowRateLimiter(self.__storage)

    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, LimitAnnotation)

    def _evaluate_key_func(self, annotation: LimitAnnotation, request: Request, kwargs: dict[str, Any]) -> str:
        kwargs = {name: value for name, value in kwargs.items() if name in annotation.parameters()}
        key_func = annotation.key()

        if annotation.has_request_parameter():
            return key_func(request=request, **kwargs)
        else:
            return key_func(**kwargs)

    async def _evaluate_limit(self, annotation: LimitAnnotation, request: Request, kwargs: dict[str, Any]):
        key = self._evaluate_key_func(annotation, request, kwargs)
        if not await self.__rate_limiter.hit(annotation.limit(), key):
            stats = await self.__rate_limiter.get_window_stats(annotation.limit(), key)
            remaining_time = int(stats.reset_time - time.time()) + 1
            raise RateLimitExceededException(reset_time=stats.reset_time, remaining_time=remaining_time)

    async def do_something(
        self, annotations: list[Annotation], request: Request, **kwargs: Any
    ):
        anns = cast(list[LimitAnnotation], annotations)

        for annotation in anns:
            await self._evaluate_limit(annotation, request, kwargs)

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
