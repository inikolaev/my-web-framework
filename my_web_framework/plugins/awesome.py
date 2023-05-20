from typing import Any

from starlette.requests import Request

from my_web_framework.annotations import Annotation, add_annotation
from my_web_framework.plugins._base import Plugin


class AwesomeAnnotation(Annotation):
    def __str__(self):
        return "AwesomeAnnotation()"

    def __repr__(self):
        return "AwesomeAnnotation()"


class AwesomePlugin(Plugin):
    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, AwesomeAnnotation)

    async def do_something(
        self, annotations: list[Annotation], request: Request, **kwargs: Any
    ):
        print(f"AwesomePlugin is being called: {annotations}, {request}, {kwargs}")


def awesome():
    def marker(f):
        add_annotation(f, AwesomeAnnotation())
        return f

    return marker
