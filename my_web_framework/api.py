from collections.abc import Callable
from typing import Mapping, Any

from my_web_framework.adapters.fastapi_adapter import FastAPIAdapter
from my_web_framework.controller import BaseController
from my_web_framework.plugins._base import Plugin


class SomeAPI:
    def __init__(self, title: str, version: str, plugins: list[Plugin] = ()) -> None:
        self.__adapter = FastAPIAdapter(title, version)
        self.__plugins = plugins.copy()

    def mount(self, controller: BaseController, path: str = "") -> None:
        self.__adapter.mount_controller(controller, path, self.__plugins)

    def on_shutdown(self, callback: Callable[..., None]) -> None:
        self.__adapter.add_event_handler("shutdown", callback)

    async def __call__(self, scope: Mapping[str, Any], receive: Callable, send: Callable) -> None:
        await self.__adapter(scope, receive, send)
