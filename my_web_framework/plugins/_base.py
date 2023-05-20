from typing import Any

from starlette.requests import Request

from my_web_framework.annotations import Annotation


class Plugin:
    def is_supported_annotation(self, annotation: Annotation) -> bool:  # noqa: ARG002
        return False

    async def do_something(
        self, annotations: list[Annotation], request: Request, **kwargs: Any,  # noqa: ARG002
    ):
        print("Plugin is being called")
