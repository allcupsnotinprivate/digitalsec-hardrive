from typing import Any, Awaitable, Callable

from aio_pika import IncomingMessage, Message
from loguru import logger
from starlette.types import ASGIApp, Receive, Scope, Send

from app.utils.tokens import generate_prefixed_uuid


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID"):
        self.app = app
        self.header_name = header_name.lower()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            raw_request_id = headers.get(self.header_name)
            request_id = raw_request_id if raw_request_id else generate_prefixed_uuid("http", length=16)

            with logger.contextualize(context_id=request_id):
                with logger.catch(reraise=True):
                    await self.app(scope, receive, send)

        else:
            await self.app(scope, receive, send)


class RabbitMQContextMiddleware:
    def __init__(self, header_name: str = "X-Request-ID", prefix: str = "rmq"):
        self.header_name = header_name
        self.prefix = prefix

    async def wrap_consumer(
        self,
        message: IncomingMessage,
        handler: Callable[[IncomingMessage], Awaitable[Any]],
    ) -> Any:
        headers = message.headers or {}
        raw_request_id = headers.get(self.header_name)
        request_id = raw_request_id or generate_prefixed_uuid(self.prefix, length=16)

        if not raw_request_id:
            message.headers[self.header_name] = request_id

        with logger.contextualize(context_id=request_id):
            with logger.catch(reraise=True):
                return await handler(message)

    def wrap_publish(self, message: Message) -> Message:
        headers = message.headers.copy() if message.headers else {}
        if self.header_name not in headers:
            headers[self.header_name] = generate_prefixed_uuid(self.prefix, length=16)
        return Message(
            body=message.body,
            headers=headers,
            correlation_id=message.correlation_id,
            content_type=message.content_type,
            content_encoding=message.content_encoding,
            delivery_mode=message.delivery_mode,
        )
