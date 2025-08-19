import abc
from typing import Mapping

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from .aClasses import AInfrastructure


class ARedisClient(AInfrastructure, redis.Redis, abc.ABC): ...  # type: ignore[misc]


class RedisClient(ARedisClient):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: str | int = 0,
        password: str | None = None,
        socket_timeout: float | None = None,
        socket_connect_timeout: float | None = None,
        socket_keepalive: bool | None = None,
        socket_keepalive_options: Mapping[int, int | bytes] | None = None,
        connection_pool: ConnectionPool | None = None,
        unix_socket_path: str | None = None,
        encoding: str = "utf-8",
        encoding_errors: str = "strict",
        decode_responses: bool = False,
    ):
        super().__init__(
            host=host,
            port=port,
            db=db,
            password=password,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            socket_keepalive=socket_keepalive,
            socket_keepalive_options=socket_keepalive_options,
            connection_pool=connection_pool,
            unix_socket_path=unix_socket_path,
            encoding=encoding,
            encoding_errors=encoding_errors,
            decode_responses=decode_responses,
        )
