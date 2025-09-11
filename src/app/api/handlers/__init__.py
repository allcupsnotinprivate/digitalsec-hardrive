import aio_pika

from app.api.handlers.documents import handle_document
from app.infrastructure import ARabbitMQ

CONSUMERS = [
    handle_document,
]


async def register_handlers(rmq: ARabbitMQ):
    for queue_name, fn in CONSUMERS:
        queue = await rmq.channel.declare_queue(queue_name, durable=True)

        async def _wrap(message: aio_pika.IncomingMessage, fn=fn):
            async with message.process():
                await fn(message)

        await queue.consume(_wrap)

__all__ = ["register_handlers"]
