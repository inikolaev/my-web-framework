import logging

import uvicorn
from starlette.requests import Request

from my_web_framework.api import SomeAPI
from my_web_framework.controller import BaseController, get
from my_web_framework.plugins.awesome import awesome, AwesomePlugin
from my_web_framework.plugins.rate_limiter import limit, RateLimiterPlugin

logger = logging.getLogger()


def get_ip_address(request: Request, id: str) -> str:
    return f"{request.client.host}::{id}"


def limit_by_ip_address(expression: str):
    """We can define custome annotations for easier reuse"""
    return limit(expression, key=get_ip_address)


class Controller(BaseController):
    @get("/payments/{id}")
    @limit("1/minute", key=get_ip_address)
    @limit("10/hour", key=get_ip_address)
    @limit_by_ip_address("100/day")
    @awesome()
    async def get_payment(self, request: Request, id: str):
        logger.info("Hello world")
        return f"Hello {id} from {request.client.host}"

    # For some reason this route overrides the route above when uncommented
    # @route("/payments", methods={"POST"})
    # @limit("2/minute")
    # async def post_payment(self):
    #     return "Hello"


api = SomeAPI(
    title="Some API", version="2023", plugins=[RateLimiterPlugin(), AwesomePlugin()]
)
api.mount(Controller(), "")

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="debug")
