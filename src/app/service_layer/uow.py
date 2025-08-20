import abc
import hashlib
from contextlib import AbstractAsyncContextManager
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import text

from app import repositories
from app.infrastructure import APostgresDatabase


class AUnitOfWorkContext(abc.ABC):
    session: AsyncSession

    agents: repositories.A_AgentsRepository
    document_chunks: repositories.ADocumentChunksRepository
    documents: repositories.ADocumentsRepository
    document_meta_prototypes: repositories.ADocumentMetaPrototypesRepository
    forwarded: repositories.AForwardedRepository
    routes: repositories.ARoutesRepository

    @abc.abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def lock_advisory(self, key: str | UUID) -> None:
        raise NotImplementedError


class UnitOfWorkContext(AUnitOfWorkContext):
    def __init__(self, session: AsyncSession):
        self.session = session
        self.agents = repositories.AgentsRepository(session)
        self.document_chunks = repositories.DocumentChunksRepository(session)
        self.documents = repositories.DocumentsRepository(session)
        self.forwarded = repositories.ForwardedRepository(session)
        self.routes = repositories.RoutesRepository(session)
        self.document_meta_prototypes = repositories.DocumentMetaPrototypesRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def lock_advisory(self, key: str | UUID) -> None:
        hex_ = key.bytes if isinstance(key, UUID) else key.encode()
        lock_key = int(hashlib.sha256(hex_).hexdigest(), 16) % (2**63)
        await self.session.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key})


class AUnitOfWork(abc.ABC):
    @abc.abstractmethod
    async def __aenter__(self) -> AUnitOfWorkContext: ...

    @abc.abstractmethod
    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None: ...


class UnitOfWork(AUnitOfWork):
    def __init__(self, postgres_database: APostgresDatabase):
        self.session_factory = postgres_database.get_session
        self._session_cm: AbstractAsyncContextManager[AsyncSession] | None = None
        self._context: AUnitOfWorkContext | None = None

    async def __aenter__(self) -> AUnitOfWorkContext:
        self._session_cm = self.session_factory()
        self.session = await self._session_cm.__aenter__()
        self._context = UnitOfWorkContext(self.session)
        return self._context

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        if self._context:
            try:
                if exc_type:
                    await self._context.rollback()
                else:
                    await self._context.commit()
            finally:
                if self._session_cm:
                    await self._session_cm.__aexit__(exc_type, exc_val, exc_tb)
                self._session_cm = None
