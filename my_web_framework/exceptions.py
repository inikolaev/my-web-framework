from collections.abc import Mapping


class HttpException(Exception):
    def __init__(
        self,
        status_code: int,
        headers: Mapping[str, str],
        content: str | bytes | dict | None,
    ) -> None:
        self.__status_code = status_code
        self.__headers = dict(headers)
        self.__content = content

    @property
    def status_code(self) -> int:
        return self.__status_code

    @property
    def headers(self) -> Mapping[str, str]:
        return dict(self.__headers)

    @property
    def content(self) -> str | bytes | dict | None:
        return self.__content
