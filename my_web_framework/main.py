import functools
import inspect
import logging
from functools import partial
from typing import Optional, cast, Any

import uvicorn
from fastapi import FastAPI, APIRouter


logger = logging.getLogger()


class EndpointAnnotation:
    def __init__(self, handler, path: str, methods: set[str]):
        self.handler = handler
        self.path = path
        self.methods = methods.copy()

    def __str__(self):
        return f"Endpoint(path={self.path},methods={self.methods})"

    def __repr__(self):
        return f"Endpoint(path={self.path},methods={self.methods})"


class Annotation:
    pass


class Endpoint:
    def __init__(self, handler, path: str, methods: set[str], annotations: list[Annotation]):
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


class LimitAnnotation(Annotation):
    def __init__(self, expression: str):
        self.__expression = expression

    def __str__(self):
        return f"LimitAnnotation(expression={self.__expression})"

    def __repr__(self):
        return f"LimitAnnotation(expression={self.__expression})"


class AwesomeAnnotation(Annotation):
    def __str__(self):
        return f"AwesomeAnnotation()"

    def __repr__(self):
        return f"AwesomeAnnotation()"


def add_annotation(f, annotation: Annotation) -> None:
    annotations = getattr(f, "_annotations", [])
    annotations.append(annotation)
    setattr(f, "_annotations", annotations)


def limit(expression: str):
    def marker(f):
        add_annotation(f, LimitAnnotation(expression))
        return f
    return marker


def awesome():
    def marker(f):
        add_annotation(f, AwesomeAnnotation())
        return f
    return marker


class ControllerMeta(type):
    def __new__(cls: type[type], name: str, bases: tuple[type[Any]], attrs: dict[str, Any]) -> "ControllerMeta":
        endpoints: list[Endpoint] = []
        for v in attrs.values():
            if inspect.isfunction(v) and hasattr(v, "_endpoint"):
                endpoint: EndpointAnnotation = getattr(v, "_endpoint")
                endpoints.append(Endpoint(
                    handler=endpoint.handler,
                    path=endpoint.path,
                    methods=endpoint.methods,
                    annotations=getattr(v, "_annotations", []),
                ))
        attrs["_endpoints"] = endpoints
        return cast(ControllerMeta, type.__new__(cls, name, bases, attrs))


class BaseController(metaclass=ControllerMeta):
    _endpoints: list[Endpoint] = []

    def endpoints(self) -> list[Endpoint]:
        return self._endpoints


class Controller(BaseController):
    @route("/payments/{id}", methods={"GET"})
    @limit("1/minute")
    @awesome()
    async def get_payment(self, id: str):
        return f"Hello {id}"

    # For some reason this route overrides the route above when uncommented
    # @route("/payments", methods={"POST"})
    # @limit("2/minute")
    # async def post_payment(self):
    #     return "Hello"


class Plugin:
    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return False

    def do_something(self):
        print(f"Plugin is being called")


class RateLimiterPlugin(Plugin):
    def is_supported_annotation(self, annotation: Annotation) -> bool:
        return isinstance(annotation, LimitAnnotation)

    def do_something(self):
        print(f"RateLimiterPlugin is being called")


class SomeAPI:
    def __init__(self, title: str, version: str, plugins: list[Plugin] = []):
        self.__api = FastAPI(title=title, version=version, openapi_url="/.well-known/schema-discovery")
        self.__plugins = plugins.copy()

    def _create_route(self, router: APIRouter, controller: BaseController, endpoint: Endpoint, path: str) -> None:
        handler = partial(endpoint.handler, controller)
        print(f"INFO:     Mounting controller endpoint at {endpoint.methods} {path}{endpoint.path}")
        plugins: set[Plugin] = set()

        print(f"INFO:     Found the following annotations:")
        for annotation in endpoint.annotations:
            print(f"INFO:     {annotation}")
            is_supported = False
            for plugin in self.__plugins:
                if plugin.is_supported_annotation(annotation):
                    is_supported = True
                    plugins.add(plugin)

            if not is_supported:
                print(f"WARN:     No plugin available that supports annotation {annotation}")

        if plugins:
            print(f"INFO:     The following plugins apply to the endpoint: {plugins}")

        @functools.wraps(handler)
        async def route_handler(*args, **kwargs):
            for plugin in plugins:
                plugin.do_something()
            return await handler(*args, **kwargs)

        router.add_api_route(path=endpoint.path, endpoint=route_handler, methods=endpoint.methods)

    def _create_router(self, controller: BaseController, path: str) -> APIRouter:
        # Some magic to mount a route and apply limiter to the route
        router = APIRouter()

        print(f"INFO:     Mounting controller at {path or '/'}")

        for endpoint in controller.endpoints():
            self._create_route(router, controller, endpoint, path)

        return router

    def mount(self, controller: BaseController, path: str):
        router = self._create_router(controller, path)
        self.__api.include_router(router, prefix=path)

    async def __call__(self, scope, receive, send) -> None:
        await self.__api(scope, receive, send)


api = SomeAPI(title="Some API", version="2023", plugins=[RateLimiterPlugin()])
api.mount(Controller(), "")

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="info")
