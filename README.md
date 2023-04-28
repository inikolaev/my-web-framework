# my-web-framework

The framework is a Python ASGI web framework with class-based routing and support for custom decorators and plugins. It provides a structured and organized approach to defining API endpoints and managing dependencies, making it easy to build scalable and maintainable APIs.

## Features

### Class-based routing

The framework uses class-based routing to provide a structured and organized approach to defining API endpoints and managing dependencies. This approach is influenced by popular Java frameworks, where developers typically define controller classes to manage endpoints and related functionality.

Each endpoint is defined as a method within a class, with the class itself representing a logical grouping of related endpoints. This can make it easier to manage and understand complex APIs, especially as they grow and evolve over time.

In addition, class-based routing allows developers to declare constructor methods within each class, which can be used to inject dependencies and manage the lifecycle of the class. This provides a clean and organized way to manage dependencies within an API, without relying on global state or other less maintainable approaches.

### Annotations

Developers can define custom decorators that add additional metadata to API endpoints. This metadata can be used by plugins to provide additional functionality or modify the behavior of the endpoint.

For example, a developer may want to define a rate limiting policy for an endpoint using a custom decorator, which can then be used by a rate limiting plugin to enforce the policy. Similarly, custom decorators can be used to add OpenAPI metadata to an endpoint, providing additional documentation and enabling features such as automatic client generation.

### Plugins

Support plugins that can extend the functionality of the framework. Currently, the framework only provides support for plugins that can intercept incoming requests, which can be useful for implementing rate-limiting and other types of request processing.

### Pluggable ASGI framework

The framework does not implement ASGI, but instead relies on existing ASGI frameworks. Currently, there is an adapter available for FastAPI. However, the framework is designed to be extensible, and there is the potential for other adapters to be developed for other ASGI frameworks in the future.

## Examples

### A simple controller

```python
import logging

import uvicorn

from my_web_framework.api import SomeAPI
from my_web_framework.controller import BaseController, get

logger = logging.getLogger()


class NameController(BaseController):
    @get("/payments/{id}")
    async def get(self, name: str):
        logger.info("Hello world")
        return f"Hello {name}!"


api = SomeAPI(title="Some API", version="2023")
api.mount(NameController())

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="debug")
```

### An example of using `limit` annotation

```python
import logging

import uvicorn
from starlette.requests import Request

from my_web_framework.api import SomeAPI
from my_web_framework.controller import BaseController, get
from my_web_framework.plugins.rate_limiter import limit, RateLimiterPlugin

logger = logging.getLogger()


def get_ip_address(request: Request) -> str:
    return request.client.host


class NameController(BaseController):
    @get("/payments/{id}")
    @limit("1/minute", key=get_ip_address)
    async def get(self, name: str):
        logger.info("Hello world")
        return f"Hello {name}!"


api = SomeAPI(title="Some API", version="2023", plugins=[RateLimiterPlugin()])
api.mount(NameController())

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="debug")
```

If we want to apply limits based on passed `name` parameter, we can pass it to the key function:

```python
import logging

import uvicorn

from my_web_framework.api import SomeAPI
from my_web_framework.controller import BaseController, get
from my_web_framework.plugins.rate_limiter import limit, RateLimiterPlugin

logger = logging.getLogger()


def get_name(name: str) -> str:
    return name


class NameController(BaseController):
    @get("/payments/{id}")
    @limit("1/minute", key=get_name)
    async def get(self, name: str):
        logger.info("Hello world")
        return f"Hello {name}!"


api = SomeAPI(title="Some API", version="2023", plugins=[RateLimiterPlugin()])
api.mount(NameController())

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="debug")
```

This allows us to parse request only once and pass any subset of the parameters defined on the handler to the key function.

It is also possible to define custom limit decorator for easier reuse:

```python
import logging

import uvicorn
from starlette.requests import Request

from my_web_framework.api import SomeAPI
from my_web_framework.controller import BaseController, get
from my_web_framework.plugins.rate_limiter import limit, RateLimiterPlugin

logger = logging.getLogger()


def get_ip_address(request: Request) -> str:
    return request.client.host


def limit_by_ip_address(expression: str):
    return limit(expression, key=get_ip_address)


class NameController(BaseController):
    @get("/payments/{id}")
    @limit_by_ip_address("1/minute")
    async def get(self, name: str):
        logger.info("Hello world")
        return f"Hello {name}!"


api = SomeAPI(title="Some API", version="2023", plugins=[RateLimiterPlugin()])
api.mount(NameController())

if __name__ == "__main__":
    uvicorn.run(api, port=5000, log_level="debug")
```