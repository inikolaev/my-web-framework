import functools

from fastapi import APIRouter, FastAPI

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
        plugins: set[Plugin] = set()

        print(f"INFO:     Found the following annotations:")
        for annotation in endpoint.annotations:
            print(f"INFO:       {annotation}")
            is_supported = False
            for plugin in self.__plugins:
                if plugin.is_supported_annotation(annotation):
                    is_supported = True
                    plugins.add(plugin)

            if not is_supported:
                print(
                    f"WARN:     No plugin available that supports annotation {annotation}"
                )

        if plugins:
            print(f"INFO:     The following plugins apply to the endpoint: {plugins}")

        @functools.wraps(handler)
        async def route_handler(*args, **kwargs):
            for plugin in plugins:
                plugin.do_something()
            return await handler(*args, **kwargs)

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

    def mount(self, controller: BaseController, path: str):
        router = self._create_router(controller, path)
        self.__api.include_router(router, prefix=path)

    async def __call__(self, scope, receive, send) -> None:
        await self.__api(scope, receive, send)
