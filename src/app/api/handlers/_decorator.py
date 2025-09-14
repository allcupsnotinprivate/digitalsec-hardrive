from collections.abc import Callable
from typing import Any, Awaitable


def consumer(
    queue_name: str,
) -> Callable[[Callable[..., Awaitable[Any]]], tuple[str, Callable[..., Awaitable[Any]]]]:
    def wrapper(
        fn: Callable[..., Awaitable[Any]],
    ) -> tuple[str, Callable[..., Awaitable[Any]]]:
        return queue_name, fn

    return wrapper
