from typing import Callable

from my_web_framework.adapters.fastapi_adapter import FastAPIAdapter
from my_web_framework.controller import BaseController
from my_web_framework.plugins._base import Plugin


class SomeAPI:
    def __init__(self, title: str, version: str, plugins: list[Plugin] = ()):
        self.__adapter = FastAPIAdapter(title, version)
        self.__plugins = plugins.copy()

    def mount(self, controller: BaseController, path: str = ""):
        self.__adapter.mount_controller(controller, path, self.__plugins)

    def on_shutdown(self, callback: Callable[..., None]) -> None:
        self.__adapter.add_event_handler("shutdown", callback)

    async def __call__(self, scope, receive, send) -> None:
        await self.__adapter(scope, receive, send)
