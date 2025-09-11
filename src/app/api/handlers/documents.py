from aio_pika import IncomingMessage

from app.infrastructure.rabbitmq import DOCUMENT_QUEUE

from ._decorator import consumer


@consumer(DOCUMENT_QUEUE)
async def handle_document(message: IncomingMessage) -> None:
    print("Received document:", message.body)
