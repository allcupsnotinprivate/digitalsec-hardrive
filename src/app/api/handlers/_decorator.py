from collections.abc import Callable
from typing import Any, Awaitable


def consumer(queue_name: str):
    def wrapper(fn: Callable[[dict], Awaitable[Any]]):
        return queue_name, fn
    return wrapper
