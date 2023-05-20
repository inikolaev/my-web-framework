import logging
from collections.abc import Callable

import uvicorn
from starlette.requests import Request

from my_web_framework.api import SomeAPI
from my_web_framework.controller import BaseController, get, route
from my_web_framework.plugins.awesome import AwesomePlugin, awesome
from my_web_framework.plugins.rate_limiter import RateLimiterPlugin, limit

logger = logging.getLogger()


def get_ip_address(request: Request) -> str:
    return request.client.host


def limit_by_ip_address(expression: str) -> Callable:
    """We can define custome annotations for easier reuse."""
    return limit(expression, key=get_ip_address)


class Controller(BaseController):
    @get("/names/{name}")
    @limit("1/minute", key=get_ip_address)
    @limit("10/hour", key=get_ip_address)
    @limit_by_ip_address("100/day")
    @awesome()
    async def get_name(self, request: Request, name: str) -> str:
        logger.info("Hello world")
        return f"Hello {name} from {request.client.host}"

    @route("/names", methods={"POST"})
    @limit_by_ip_address("2/minute")
    async def post_names(self) -> str:
        return "Hello"


def shutdown() -> None:
    logger.info("Shutting down")


api = SomeAPI(
    title="Some API", version="2023", plugins=[RateLimiterPlugin(), AwesomePlugin()],
)
api.mount(Controller())
api.on_shutdown(shutdown)


if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="debug")
