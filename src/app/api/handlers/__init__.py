from collections.abc import Callable
from typing import Any, Awaitable

import aio_pika

from app.infrastructure import ARabbitMQ

from .documents import handle_document
from .investigations import handle_investigation

CONSUMERS = [handle_document, handle_investigation]


def make_wrapper(
    fn: Callable[[aio_pika.IncomingMessage], Awaitable[Any]],
) -> Callable[[aio_pika.IncomingMessage], Awaitable[None]]:
    async def _wrap(message: aio_pika.IncomingMessage) -> None:
        async with message.process():
            await fn(message)

    return _wrap


async def register_handlers(rmq: ARabbitMQ) -> None:
    for queue_name, fn in CONSUMERS:
        await rmq.consume(queue_name, make_wrapper(fn))


__all__ = ["register_handlers"]
