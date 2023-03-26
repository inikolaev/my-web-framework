import inspect
from typing import Any, Callable, cast

from starlette.requests import Request

from my_web_framework.annotations import Annotation, add_annotation
from my_web_framework.plugins._base import Plugin


class RateLimiterPlugin(Plugin):
    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, LimitAnnotation)

    def do_something(self, annotations: list[Annotation], request: Request, **kwargs: Any):
        anns = cast(list[LimitAnnotation], annotations)

        all_kwargs = {
            "request": request,
            **kwargs,
        }

        for annotation in anns:
            parameters = all_kwargs.keys() & annotation.parameters()
            key_func = annotation.key()
            key_func(**{
                name: value for name, value in all_kwargs.items() if name in parameters
            })

        print(f"RateLimiterPlugin is being called: {annotations}, {request}, {kwargs}")


class LimitAnnotation(Annotation):
    def __init__(self, expression: str, key: Callable, parameters: set[str]):
        self.__expression = expression
        self.__key = key
        self.__parameters = frozenset(parameters.copy())

    def __str__(self):
        return f"LimitAnnotation(expression={self.__expression}, parameters={self.__parameters})"

    def __repr__(self):
        return f"LimitAnnotation(expression={self.__expression}, parameters={self.__parameters})"

    def key(self) -> Callable:
        return self.__key

    def parameters(self) -> frozenset[str]:
        return self.__parameters


def limit(expression: str, key: Callable):
    def marker(method: Callable) -> Callable:
        key_parameters = {name for name, value in inspect.signature(key).parameters.items() if name != "self"}
        key_parameters_without_request = {name for name in key_parameters if name != "request"}
        method_parameters = {name for name, value in inspect.signature(method).parameters.items() if name != "self"}

        if not key_parameters_without_request.issubset(method_parameters):
            raise ValueError(f"Key function `{key.__qualname__}` expects parameters not present in handler `{method.__qualname__}`: {key_parameters_without_request.difference(method_parameters)}")

        add_annotation(method, LimitAnnotation(expression, key, key_parameters))
        return method

    return marker
