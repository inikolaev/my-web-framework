import inspect
from typing import Any, cast

from my_web_framework.annotations import Annotation


class EndpointAnnotation:
    def __init__(self, handler, path: str, methods: set[str]):
        self.handler = handler
        self.path = path
        self.methods = methods.copy()

    def __str__(self):
        return f"Endpoint(path={self.path},methods={self.methods})"

    def __repr__(self):
        return f"Endpoint(path={self.path},methods={self.methods})"


class Endpoint:
    def __init__(
        self, handler, path: str, methods: set[str], annotations: list[Annotation]
    ):
        self.handler = handler
        self.path = path
        self.methods = methods.copy()
        self.annotations = annotations.copy()

    def __str__(self):
        return f"Endpoint(path={self.path},methods={self.methods}, annotations={self.annotations})"

    def __repr__(self):
        return f"Endpoint(path={self.path},methods={self.methods}, annotations={self.annotations})"


def route(path: str, methods: set[str]):
    def marker(f):
        setattr(f, "_endpoint", EndpointAnnotation(f, path, methods))
        return f

    return marker


class ControllerMeta(type):
    def __new__(
        cls: type[type], name: str, bases: tuple[type[Any]], attrs: dict[str, Any]
    ) -> "ControllerMeta":
        endpoints: list[Endpoint] = []
        for v in attrs.values():
            if inspect.isfunction(v) and hasattr(v, "_endpoint"):
                endpoint: EndpointAnnotation = getattr(v, "_endpoint")
                endpoints.append(
                    Endpoint(
                        handler=endpoint.handler,
                        path=endpoint.path,
                        methods=endpoint.methods,
                        annotations=getattr(v, "_annotations", []),
                    )
                )
        attrs["_endpoints"] = endpoints
        return cast(ControllerMeta, type.__new__(cls, name, bases, attrs))


class BaseController(metaclass=ControllerMeta):
    _endpoints: list[Endpoint] = []

    def endpoints(self) -> list[Endpoint]:
        return self._endpoints
