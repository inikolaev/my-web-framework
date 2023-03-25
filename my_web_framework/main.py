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


class Limiter:
    def limit(self, limits: list[LimitAnnotation]):
        print(f"Limiter is being called with the following limits: {limits}")


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


class SomeAPI:
    def __init__(self, title: str, version: str, limiter: Optional[Limiter] = None):
        self.__api = FastAPI(title=title, version=version, openapi_url="/.well-known/schema-discovery")
        self.__limiter = limiter

    def _create_route(self, router: APIRouter, controller: BaseController, endpoint: Endpoint, path: str) -> None:
        handler = partial(endpoint.handler, controller)
        print(f"Mounting controller endpoint at {endpoint.methods} {path}{endpoint.path}")
        limits = []

        print(f"  Found the following annotations:")
        for annotation in endpoint.annotations:
            print(f"    {annotation}")
            # For each annotation we should find a plugin that supports it
            # and create a list of plugins that have to be called for the endpoint
            if isinstance(annotation, LimitAnnotation):
                limits.append(annotation)

        if limits:
            print(f"  Detected the following endpoint limits: {limits}")

        # Instead of just limiter, we should be able to handle different annotations here
        if self.__limiter:
            @functools.wraps(handler)
            async def route_handler(*args, **kwargs):
                self.__limiter.limit(limits)
                return await handler(*args, **kwargs)
        else:
            @functools.wraps(handler)
            async def route_handler(*args, **kwargs):
                return await handler(*args, **kwargs)

        router.add_api_route(path=endpoint.path, endpoint=route_handler, methods=endpoint.methods)

    def _create_router(self, controller: BaseController, path: str) -> APIRouter:
        # Some magic to mount a route and apply limiter to the route
        router = APIRouter()

        print(f"Mounting controller at {path or '/'}")

        for endpoint in controller.endpoints():
            self._create_route(router, controller, endpoint, path)

        return router

    def mount(self, controller: BaseController, path: str):
        router = self._create_router(controller, path)
        self.__api.include_router(router, prefix=path)

    async def __call__(self, scope, receive, send) -> None:
        await self.__api(scope, receive, send)


api = SomeAPI(title="Some API", version="2023", limiter=Limiter())
api.mount(Controller(), "")

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="info")
