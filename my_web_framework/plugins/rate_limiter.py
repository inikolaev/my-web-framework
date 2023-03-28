import inspect
from typing import Any, Callable, cast

from starlette.requests import Request

from my_web_framework.annotations import Annotation, add_annotation
from my_web_framework.plugins._base import Plugin


class LimitAnnotation(Annotation):
    def __init__(self, expression: str, key: Callable, parameters: set[str]):
        self.__expression = expression
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


class RateLimiterPlugin(Plugin):
    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, LimitAnnotation)

    def _evaluate_key_func(self, annotation: LimitAnnotation, request: Request, kwargs: dict[str, Any]) -> str:
        kwargs = {name: value for name, value in kwargs.items() if name in annotation.parameters()}
        key_func = annotation.key()

        if annotation.has_request_parameter():
            return key_func(request=request, **kwargs)
        else:
            return key_func(**kwargs)

    def _evaluate_limit(self, annotation: LimitAnnotation, request: Request, kwargs: dict[str, Any]):
        self._evaluate_key_func(annotation, request, kwargs)

    def do_something(
        self, annotations: list[Annotation], request: Request, **kwargs: Any
    ):
        anns = cast(list[LimitAnnotation], annotations)

        for annotation in anns:
            self._evaluate_limit(annotation, request, kwargs)

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
