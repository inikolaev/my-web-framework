from typing import Any

from starlette.requests import Request

from my_web_framework.annotations import Annotation, add_annotation
from my_web_framework.plugins._base import Plugin


class RateLimiterPlugin(Plugin):
    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, LimitAnnotation)

    def do_something(self, annotations: list[Annotation], request: Request, **kwargs: Any):
        print(f"RateLimiterPlugin is being called: {annotations}, {request}, {kwargs}")


class LimitAnnotation(Annotation):
    def __init__(self, expression: str):
        self.__expression = expression

    def __str__(self):
        return f"LimitAnnotation(expression={self.__expression})"

    def __repr__(self):
        return f"LimitAnnotation(expression={self.__expression})"


def limit(expression: str):
    def marker(f):
        add_annotation(f, LimitAnnotation(expression))
        return f

    return marker
