import inspect
from collections.abc import Callable

from limits import RateLimitItem, parse_many

from my_web_framework.annotations import Annotation, add_annotation


class _LimitAnnotation(Annotation):
    def __init__(self, expression: str, key: Callable, parameters: set[str]) -> None:
        self.__expression = expression
        self.__limits = parse_many(expression)
        self.__key = key
        self.__parameters = frozenset(parameters.copy())
        self.__has_request_parameter = "request" in self.__parameters

    def __str__(self) -> str:
        return (
    f"LimitAnnotation(expression={self.__expression},"
    f" parameters={self.__parameters})"
    )

    def __repr__(self) -> str:
        return (
    f"LimitAnnotation(expression={self.__expression},"
    f" parameters={self.__parameters})"
    )

    def key(self) -> Callable:
        return self.__key

    def parameters(self) -> frozenset[str]:
        return self.__parameters

    def has_request_parameter(self) -> bool:
        return self.__has_request_parameter

    def limits(self) -> list[RateLimitItem]:
        return self.__limits


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
            msg = f"Key function `{key.__qualname__}`expects parameters not present in handler `{{method.__qualname__}}`:{{key_parameters_without_request.difference(method_parameters)}}"
            raise ValueError(
        msg,
        )

        add_annotation(method, _LimitAnnotation(expression, key, key_parameters))
        return method

    return marker
