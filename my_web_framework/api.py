import functools
import inspect
from collections import defaultdict
from typing import Callable

from fastapi import APIRouter, FastAPI
from starlette.requests import Request

from my_web_framework.annotations import Annotation
from my_web_framework.controller import BaseController, Endpoint
from my_web_framework.plugins._base import Plugin


class SomeAPI:
    def __init__(self, title: str, version: str, plugins: list[Plugin] = []):
        self.__api = FastAPI(
            title=title, version=version, openapi_url="/.well-known/schema-discovery"
        )
        self.__plugins = plugins.copy()

    def _create_route(
        self,
        router: APIRouter,
        controller: BaseController,
        endpoint: Endpoint,
        path: str,
    ) -> None:
        handler = functools.partial(endpoint.handler, controller)
        print(
            f"INFO:     Mounting controller endpoint at {endpoint.methods} {path}{endpoint.path}"
        )
        plugins: dict[Plugin, list[Annotation]] = defaultdict(list)

        print(f"INFO:     Found the following annotations:")
        for annotation in endpoint.annotations:
            print(f"INFO:       {annotation}")
            is_supported = False
            for plugin in self.__plugins:
                if plugin.is_supported_annotation(annotation):
                    is_supported = True
                    plugins[plugin].append(annotation)

            if not is_supported:
                print(
                    f"WARN:     No plugin available that supports annotation {annotation}"
                )

        if plugins:
            print(f"INFO:     The following plugins apply to the endpoint: {plugins}")

        # Check if endpoint handler declared request parameter
        signature = inspect.signature(handler)
        expects_request = "request" in signature.parameters

        @functools.wraps(handler)
        async def route_handler(request: Request, **kwargs):
            for plugin, annotations in plugins.items():
                plugin.do_something(annotations, request, **kwargs)

            if expects_request:
                # endpoint handler expects request parameter, we have to pass it explicitly here
                return await handler(request=request, **kwargs)
            else:
                # otherwise pass declared parameters only
                return await handler(**kwargs)

        if not expects_request:
            # We want to be able to access raw request from plugins,
            # so we update signature of the endpoint handler to include
            # request object there to convince FastAPI to pass request
            route_handler.__signature__ = signature.replace(
                parameters=(
                    inspect.Parameter(
                        "request",
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=Request,
                    ),
                )
                + tuple(signature.parameters.values())
            )

        router.add_api_route(
            path=endpoint.path, endpoint=route_handler, methods=endpoint.methods
        )

    def _create_router(self, controller: BaseController, path: str) -> APIRouter:
        # Some magic to mount a route and apply limiter to the route
        router = APIRouter()

        print(f"INFO:     Mounting controller at {path or '/'}")

        for endpoint in controller.endpoints():
            self._create_route(router, controller, endpoint, path)

        return router

    def mount(self, controller: BaseController, path: str = ""):
        router = self._create_router(controller, path)
        self.__api.include_router(router, prefix=path)

    def on_shutdown(self, callback: Callable[..., None]) -> None:
        self.__api.add_event_handler("shutdown", callback)

    async def __call__(self, scope, receive, send) -> None:
        await self.__api(scope, receive, send)
