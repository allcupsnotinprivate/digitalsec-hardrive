import asyncio

from app.api.handlers import handle_document
from app.container import container
from app.infrastructure.rabbitmq import DOCUMENT_QUEUE, ARabbitMQ


async def main() -> None:
    async with container:
        with container.sync_context() as ctx:
            rabbit: ARabbitMQ = ctx.resolve(ARabbitMQ)
        await rabbit.startup()
        await rabbit.channel.set_qos(prefetch_count=1)
        queue = await rabbit.channel.get_queue(DOCUMENT_QUEUE)
        await queue.consume(lambda message: handle_document(message))
        try:
            await asyncio.Future()
        finally:
            await rabbit.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
