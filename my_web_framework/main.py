import logging

import uvicorn

from my_web_framework.api import SomeAPI
from my_web_framework.controller import route, BaseController
from my_web_framework.plugins.awesome import awesome, AwesomePlugin
from my_web_framework.plugins.rate_limiter import limit, RateLimiterPlugin

logger = logging.getLogger()


class Controller(BaseController):
    @route("/payments/{id}", methods={"GET"})
    @limit("1/minute")
    @awesome()
    async def get_payment(self, id: str):
        return f"Hello {id}"

    # For some reason this route overrides the route above when uncommented
    # @route("/payments", methods={"POST"})
    # @limit("2/minute")
    # async def post_payment(self):
    #     return "Hello"


api = SomeAPI(title="Some API", version="2023", plugins=[RateLimiterPlugin(), AwesomePlugin()])
api.mount(Controller(), "")

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="info")
