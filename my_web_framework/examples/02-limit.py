import logging

import uvicorn
from starlette.requests import Request

from my_web_framework.api import SomeAPI
from my_web_framework.controller import BaseController, get
from my_web_framework.plugins.rate_limiter import RateLimiterPlugin, limit

logger = logging.getLogger()


def get_ip_address(request: Request) -> str:
    return request.client.host


class NameController(BaseController):
    @get("/names/{name}")
    @limit("1/minute", key=get_ip_address)
    async def get(self, name: str):
        logger.info("Hello world")
        return f"Hello {name}!"


api = SomeAPI(title="Some API", version="2023", plugins=[RateLimiterPlugin()])
api.mount(NameController())

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="debug")
