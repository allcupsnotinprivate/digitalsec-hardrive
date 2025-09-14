import json
from uuid import UUID

from aio_pika import IncomingMessage
from aioinject import Injected, inject

from app.container.container import InvestigationSemaphore
from app.infrastructure.rabbitmq import INVESTIGATION_QUEUE
from app.service_layer import ARoutesService

from ._decorator import consumer


@consumer(INVESTIGATION_QUEUE)
@inject
async def handle_investigation(
    message: IncomingMessage, semaphore: Injected[InvestigationSemaphore], routes_service: Injected[ARoutesService]
) -> None:
    data = json.loads(message.body)
    route_id = UUID(data["route_id"])
    # TODO: replace with more reliable mechanism
    async with semaphore:
        await routes_service.investigate(route_id)
