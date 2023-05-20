import functools
import inspect
from collections.abc import Callable, Mapping

from fastapi import APIRouter, FastAPI
from starlette.requests import Request
from starlette.responses import Response

from my_web_framework.adapters.base_adapter import BaseAdapter
from my_web_framework.annotations import Annotation
from my_web_framework.controller import BaseController, Endpoint
from my_web_framework.exceptions import HttpException
from my_web_framework.plugins._base import Plugin


class FastAPIAdapter(BaseAdapter):
    def __init__(self, title: str, version: str) -> None:
        self.__api = FastAPI(
            title=title, version=version, openapi_url="/.well-known/schema-discovery",
        )

    def _wrap(
        self, handler: Callable, plugins: Mapping[Plugin, list[Annotation]],
    ) -> Callable:
        # Check if endpoint handler declared request parameter
        signature = inspect.signature(handler)
        expects_request = "request" in signature.parameters

        @functools.wraps(handler)
        async def route_handler(request: Request, **kwargs):
            try:
                for plugin, annotations in plugins.items():
                    await plugin.do_something(annotations, request, **kwargs)

                if expects_request:
                    # endpoint handler expects request parameter,
                    # we have to pass it explicitly here
                    return await handler(request=request, **kwargs)
                else:
                    # otherwise pass declared parameters only
                    return await handler(**kwargs)
            except HttpException as e:
                return Response(
                    status_code=e.status_code,
                    headers=e.headers,
                    content=e.content,
                )

        if not expects_request:
            # We want to be able to access raw request from plugins,
            # so we update signature of the endpoint handler to include
            # request object there to convince FastAPI to pass request
            route_handler.__signature__ = signature.replace(
                parameters=(inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request), *tuple(signature.parameters.values())),
            )

        return route_handler

    def _create_route(
        self,
        router: APIRouter,
        controller: BaseController,
        endpoint: Endpoint,
        path: str,
        plugins: list[Plugin],
    ) -> None:
        handler = functools.partial(endpoint.handler, controller)
        print(
            "INFO: Mounting controller endpoint at "
            f"{endpoint.methods} {path}{endpoint.path}",
        )
        supported_plugins = self._supported_plugins(endpoint, plugins)

        if supported_plugins:
            print(
                "INFO: The following plugins apply to the endpoint: "
                f"{supported_plugins}",
            )

        route_handler = self._wrap(handler, supported_plugins)

        router.add_api_route(
            path=endpoint.path, endpoint=route_handler, methods=endpoint.methods,
        )

    def _create_router(
        self, controller: BaseController, path: str, plugins: list[Plugin],
    ) -> APIRouter:
        # Some magic to mount a route and apply limiter to the route
        router = APIRouter()

        print(f"INFO:     Mounting controller at {path or '/'}")

        for endpoint in controller.endpoints():
            self._create_route(router, controller, endpoint, path, plugins)

        return router

    def mount_controller(
        self, controller: BaseController, path: str, plugins: list[Plugin],
    ) -> None:
        router = self._create_router(controller, path, plugins)
        self.__api.include_router(router, prefix=path)

    async def __call__(self, scope, receive, send) -> None:
        await self.__api(scope, receive, send)

    def add_event_handler(self, event: str, callback: Callable[..., None]):
        self.__api.add_event_handler(event, callback)
