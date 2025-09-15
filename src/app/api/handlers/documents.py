import json
from uuid import UUID

from aio_pika import IncomingMessage
from aioinject import Injected, inject

from app.container.keys import DocumentsSemaphore
from app.infrastructure.rabbitmq import DOCUMENT_QUEUE, FAILED_DOCUMENT_QUEUE, INVESTIGATION_QUEUE, ARabbitMQ
from app.service_layer import ADocumentsService, ARoutesService

from ._decorator import consumer


@consumer(DOCUMENT_QUEUE)
@inject
async def handle_document(
    message: IncomingMessage,
    semaphore: Injected[DocumentsSemaphore],
    documents_service: Injected[ADocumentsService],
    routes_service: Injected[ARoutesService],
    rmq: Injected[ARabbitMQ],
) -> None:
    data = json.loads(message.body)
    name = data.get("name")
    content = data.get("content")
    sender_id_raw = data.get("sender_id")

    sender_id = UUID(sender_id_raw) if sender_id_raw else None

    headers = {}
    if request_id := message.headers.get("X-Request-ID"):
        headers["X-Request-ID"] = request_id

    try:
        async with semaphore:
            document = await documents_service.admit(name=name, content=content)
        route = await routes_service.initialize(document_id=document.id, sender_id=sender_id)
    except Exception:
        await rmq.publish_message(FAILED_DOCUMENT_QUEUE, data, headers=headers)
        return

    await rmq.publish_message(INVESTIGATION_QUEUE, {"route_id": str(route.id)}, headers=headers)
