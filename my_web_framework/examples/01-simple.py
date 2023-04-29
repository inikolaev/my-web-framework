import logging

import uvicorn

from my_web_framework.api import SomeAPI
from my_web_framework.controller import BaseController, get

logger = logging.getLogger()


class NameController(BaseController):
    @get("/names/{name}")
    async def get(self, name: str):
        logger.info("Hello world")
        return f"Hello {name}!"


api = SomeAPI(title="Some API", version="2023")
api.mount(NameController())

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="debug")
