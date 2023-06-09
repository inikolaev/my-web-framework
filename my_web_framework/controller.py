import inspect
from collections.abc import Callable
from typing import Any, cast

from my_web_framework.annotations import Annotation, add_annotation


class EndpointAnnotation(Annotation):
    def __init__(self, handler: Callable, path: str, methods: set[str]) -> None:
        self.handler = handler
        self.path = path
        self.methods = methods.copy()

    def __str__(self) -> str:
        return f"Endpoint(path={self.path},methods={self.methods})"

    def __repr__(self) -> str:
        return f"Endpoint(path={self.path},methods={self.methods})"


class Endpoint:
    def __init__(
        self, handler, path: str, methods: set[str], annotations: list[Annotation],
    ) -> None:
        self.handler = handler
        self.path = path
        self.methods = methods.copy()
        self.annotations = annotations.copy()

    def __str__(self) -> str:
        return (
            f"Endpoint(path={self.path},methods={self.methods},"
            f" annotations={self.annotations})"
        )

    def __repr__(self) -> str:
        return (
            f"Endpoint(path={self.path},methods={self.methods},"
            f" annotations={self.annotations})"
        )


def route(path: str, methods: set[str]) -> Callable:
    def marker(f):
        add_annotation(f, EndpointAnnotation(f, path, methods))
        return f

    return marker


def get(path: str) -> Callable:
    return route(path, methods={"GET"})


def post(path: str) -> Callable:
    return route(path, methods={"POST"})


def put(path: str) -> Callable:
    return route(path, methods={"PUT"})


def patch(path: str) -> Callable:
    return route(path, methods={"PATCH"})


def delete(path: str) -> Callable:
    return route(path, methods={"DELETE"})


def option(path: str) -> Callable:
    return route(path, methods={"OPTION"})


class ControllerMeta(type):
    def __new__(
        cls: type[type], name: str, bases: tuple[type[Any]], attrs: dict[str, Any],
    ) -> "ControllerMeta":
        endpoints: list[Endpoint] = []
        for v in attrs.values():
            if inspect.isfunction(v) and hasattr(v, "_annotations"):
                annotations: list[Annotation] = getattr(v, "_annotations", [])

                for annotation in annotations:
                    if isinstance(annotation, EndpointAnnotation):
                        endpoints.append(
                            Endpoint(
                                handler=annotation.handler,
                                path=annotation.path,
                                methods=annotation.methods,
                                annotations=annotations,
                            ),
                        )
        attrs["_endpoints"] = endpoints
        return cast(ControllerMeta, type.__new__(cls, name, bases, attrs))


class BaseController(metaclass=ControllerMeta):
    _endpoints: list[Endpoint] = []

    def endpoints(self) -> list[Endpoint]:
        return self._endpoints
