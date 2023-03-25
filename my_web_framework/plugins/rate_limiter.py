from my_web_framework.annotations import Annotation, add_annotation
from my_web_framework.plugins._base import Plugin


class RateLimiterPlugin(Plugin):
    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, LimitAnnotation)

    def do_something(self):
        print(f"RateLimiterPlugin is being called")


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
