from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable, Mapping

from my_web_framework.annotations import Annotation
from my_web_framework.controller import BaseController, Endpoint
from my_web_framework.plugins._base import Plugin


class BaseAdapter(ABC):
    def _supported_plugins(
        self, endpoint: Endpoint, plugins: list[Plugin]
    ) -> Mapping[Plugin, list[Annotation]]:
        supported_plugins: dict[Plugin, list[Annotation]] = defaultdict(list)

        print("INFO:     Found the following annotations:")
        for annotation in endpoint.annotations:
            print(f"INFO:       {annotation}")
            is_supported = False
            for plugin in plugins:
                if plugin.is_supported_annotation(annotation):
                    is_supported = True
                    supported_plugins[plugin].append(annotation)

            if not is_supported:
                print(
                    f"WARN: No plugin available that supports annotation {annotation}"
                )

        return supported_plugins

    @abstractmethod
    def mount_controller(
        self, controller: BaseController, path: str, plugins: list[Plugin]
    ) -> None:
        ...

    @abstractmethod
    async def __call__(self, scope, receive, send) -> None:
        ...

    @abstractmethod
    def add_event_handler(self, event: str, callback: Callable[..., None]):
        ...
