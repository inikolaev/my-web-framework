import functools
import inspect
import logging
from functools import partial
from typing import Optional, cast, Any

import uvicorn
from fastapi import FastAPI, APIRouter


logger = logging.getLogger()


class Endpoint:
    def __init__(self, handler, path: str, methods: set[str]):
        self.handler = handler
        self.path = path
        self.methods = methods.copy()

    def __str__(self):
        return f"Endpoint(path={self.path},methods={self.methods})"

    def __repr__(self):
        return f"Endpoint(path={self.path},methods={self.methods})"


def route(path: str, methods: set[str]):
    def marker(f):
        setattr(f, "_endpoint", Endpoint(f, path, methods))
        return f

    return marker


class Limit:
    def __init__(self, expression: str):
        self.__expression = expression

    def __str__(self):
        return f"Limit(expression={self.__expression})"

    def __repr__(self):
        return f"Limit(expression={self.__expression})"


class Limiter:
    def limit(self, limits: list[Limit]):
        print(f"Limiter is being called with the following limits: {limits}")


def limit(expression: str):
    def marker(f):
        limits = getattr(f, "_limits", [])
        limits.append(Limit(expression))
        setattr(f, "_limits", limits)
        return f
    return marker


class ControllerMeta(type):
    def __new__(cls: type[type], name: str, bases: tuple[type[Any]], attrs: dict[str, Any]) -> "ControllerMeta":
        endpoints: list[Endpoint] = []
        for v in attrs.values():
            if inspect.isfunction(v) and hasattr(v, "_endpoint"):
                endpoints.append(v._endpoint)
        attrs["_endpoints"] = endpoints
        return cast(ControllerMeta, type.__new__(cls, name, bases, attrs))


class BaseController(metaclass=ControllerMeta):
    _endpoints: list[Endpoint] = []

    def endpoints(self) -> list[Endpoint]:
        return self._endpoints


class Controller(BaseController):
    @route("/payments/{id}", methods={"GET"})
    @limit("1/minute")
    async def get_payment(self, id: str):
        return f"Hello {id}"

    # @route("/payments", methods={"POST"})
    # @limit("2/minute")
    # async def post_payment(self):
    #     return "Hello"


class SomeAPI:
    def __init__(self, title: str, version: str, limiter: Optional[Limiter] = None):
        self.__api = FastAPI(title=title, version=version, openapi_url="/.well-known/schema-discovery")
        self.__limiter = limiter

    def mount(self, controller: BaseController, path: str):
        # Some magic to mount a route and apply limiter to the route
        router = APIRouter()

        print(f"Mounting controller at {path or '/'}")

        for endpoint in controller.endpoints():
            handler = partial(endpoint.handler, controller)
            print(f"Mounting controller endpoint at {endpoint.methods} {path}{endpoint.path}")
            limits = getattr(endpoint.handler, "_limits", [])

            if limits:
                print(f"  Detected the following endpoint limits: {limits}")

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

        self.__api.include_router(router, prefix=path)

    async def __call__(self, scope, receive, send) -> None:
        await self.__api(scope, receive, send)


api = SomeAPI(title="Some API", version="2023", limiter=Limiter())
api.mount(Controller(), "")

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="info")
