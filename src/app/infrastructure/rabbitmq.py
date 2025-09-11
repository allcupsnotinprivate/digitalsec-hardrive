import abc
import json

import aio_pika
from aio_pika import ExchangeType

from .aClasses import AInfrastructure

DOCUMENT_EXCHANGE = "documents"
DOCUMENT_QUEUE = "documents"
FAILED_DOCUMENT_QUEUE = "documents_failed"
INVESTIGATION_COMPLETED_QUEUE = "investigation_completed"
DOCUMENT_FAILED_NOTIFICATION_QUEUE = "document_failed"


class ARabbitMQ(AInfrastructure):

    @property
    @abc.abstractmethod
    def channel(self) -> aio_pika.Channel:
        raise NotImplementedError

    @abc.abstractmethod
    async def startup(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def publish_message(
        self, routing_key: str, body: dict | str | bytes, *, correlation_id: str | None = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def shutdown(self) -> None:
        raise NotImplementedError


class RabbitMQ(ARabbitMQ):

    def __init__(self, url: str) -> None:
        self._url = url
        self._connection: aio_pika.RobustConnection | None = None
        self._channel: aio_pika.Channel | None = None
        self._exchange: aio_pika.Exchange | None = None

    @property
    def channel(self) -> aio_pika.Channel:
        assert self._channel is not None
        return self._channel

    async def startup(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            DOCUMENT_EXCHANGE, ExchangeType.DIRECT
        )
        await self._declare_and_bind_queue(DOCUMENT_QUEUE)
        await self._declare_and_bind_queue(FAILED_DOCUMENT_QUEUE)
        await self._declare_and_bind_queue(INVESTIGATION_COMPLETED_QUEUE)
        await self._declare_and_bind_queue(DOCUMENT_FAILED_NOTIFICATION_QUEUE)

    async def _declare_and_bind_queue(self, name: str) -> None:
        assert self._exchange is not None
        queue = await self._channel.declare_queue(name, durable=True)
        await queue.bind(self._exchange, routing_key=name)

    async def publish_message(
        self, routing_key: str, body: dict | str | bytes, *, correlation_id: str | None = None
    ) -> None:
        payload = json.dumps(body) if isinstance(body, dict) else body
        assert self._exchange is not None
        data = payload.encode() if isinstance(payload, str) else payload
        message = aio_pika.Message(body=data, correlation_id=correlation_id)
        await self._exchange.publish(message, routing_key=routing_key)

    async def shutdown(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._exchange = None
