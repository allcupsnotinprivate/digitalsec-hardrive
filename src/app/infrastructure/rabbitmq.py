import abc
import json
from typing import Any, Awaitable, Callable

import aio_pika

from app.middlewares import RabbitMQContextMiddleware

from .aClasses import AInfrastructure

DOCUMENT_EXCHANGE = "documents"
# queues
DOCUMENT_QUEUE = "documents"
INVESTIGATION_QUEUE = "investigations"
FAILED_DOCUMENT_QUEUE = "documents.failed"


class ARabbitMQ(AInfrastructure):
    @property
    @abc.abstractmethod
    def channel(self) -> aio_pika.abc.AbstractChannel:
        raise NotImplementedError

    @abc.abstractmethod
    async def startup(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def publish_message(
        self,
        routing_key: str,
        body: dict[Any, Any] | str | bytes,
        *,
        correlation_id: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def consume(self, queue_name: str, handler: Callable[[aio_pika.IncomingMessage], Awaitable[Any]]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def shutdown(self) -> None:
        raise NotImplementedError


class RabbitMQ(ARabbitMQ):
    def __init__(self, url: str) -> None:
        self._url = url
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchange: aio_pika.abc.AbstractExchange | None = None
        self._middleware = RabbitMQContextMiddleware()

    @property
    def channel(self) -> aio_pika.abc.AbstractChannel:
        if self._channel is None:
            raise RuntimeError("Channel is not initialized")
        return self._channel

    async def startup(self) -> None:
        self._connection = await aio_pika.connect_robust(self._url)
        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(DOCUMENT_EXCHANGE, aio_pika.ExchangeType.DIRECT)
        await self._declare_and_bind_queue(DOCUMENT_QUEUE)
        await self._declare_and_bind_queue(INVESTIGATION_QUEUE)
        await self._declare_and_bind_queue(FAILED_DOCUMENT_QUEUE)

    async def _declare_and_bind_queue(self, name: str) -> None:
        if self._exchange is None:
            raise RuntimeError("Exchange is not initialized")
        queue = await self._channel.declare_queue(name, durable=True)  # type: ignore[union-attr]
        await queue.bind(self._exchange, routing_key=name)

    async def publish_message(
        self,
        routing_key: str,
        body: dict[Any, Any] | str | bytes,
        *,
        correlation_id: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        payload = json.dumps(body) if isinstance(body, dict) else body
        if self._exchange is None:
            raise RuntimeError("Exchange is not initialized")
        data = payload.encode() if isinstance(payload, str) else payload

        message = aio_pika.Message(body=data, correlation_id=correlation_id, headers=headers or {})

        await self._exchange.publish(message, routing_key=routing_key)

    async def consume(self, queue_name: str, handler: Callable[[aio_pika.IncomingMessage], Awaitable[Any]]) -> None:
        if self._channel is None:
            raise RuntimeError("Channel is not initialized")

        queue = await self._channel.get_queue(queue_name)
        await queue.consume(lambda msg: self._middleware.wrap_consumer(msg, handler))  # type: ignore[arg-type]

    async def shutdown(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._channel = None
            self._exchange = None
