from my_web_framework.annotations import Annotation, add_annotation
from my_web_framework.plugins._base import Plugin


class AwesomeAnnotation(Annotation):
    def __str__(self):
        return f"AwesomeAnnotation()"

    def __repr__(self):
        return f"AwesomeAnnotation()"


class AwesomePlugin(Plugin):
    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, AwesomeAnnotation)

    def do_something(self):
        print(f"AwesomePlugin is being called")


def awesome():
    def marker(f):
        add_annotation(f, AwesomeAnnotation())
        return f
    return marker
