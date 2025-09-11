import json
from uuid import UUID

import aio_pika
from loguru import logger

from app.container import container
from app.infrastructure.rabbitmq import (
    DOCUMENT_FAILED_NOTIFICATION_QUEUE,
    FAILED_DOCUMENT_QUEUE,
    ARabbitMQ,
)
from app.service_layer import ADocumentsService, ARoutesService
from app.tasks.routes import investigate_route


async def handle_document(message: aio_pika.IncomingMessage,) -> None:
    with container.sync_context() as ctx:
        rabbit: ARabbitMQ = ctx.resolve(ARabbitMQ)
        docs: ADocumentsService = ctx.resolve(ADocumentsService)
        routes: ARoutesService = ctx.resolve(ARoutesService)

    correlation_id = message.correlation_id
    async with message.process():
        try:
            payload = json.loads(message.body)
            name = payload["name"]
            content = payload["content"]
            sender_id = payload.get("sender_id")

            document = await docs.admit(name=name, content=content)
            route = await routes.initialize(
                document.id, UUID(sender_id) if sender_id else None
            )

            if sender_id:
                investigate_route.apply_async(args=(str(route.id), sender_id))
        except Exception as exc:  # pragma: no cover - rare
            logger.exception("Failed to process document", exc=exc)
            await rabbit.publish_message(
                FAILED_DOCUMENT_QUEUE, message.body, correlation_id=correlation_id
            )
            await rabbit.publish_message(
                DOCUMENT_FAILED_NOTIFICATION_QUEUE,
                {"status": "failed", "reason": str(exc)},
                correlation_id=correlation_id,
            )
