import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BOOLEAN, FLOAT, TIMESTAMP, VARCHAR, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import BYTEA, ENUM, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.utils.timestamps import now_with_tz

from .enums import ProcessStatus

ProcessStatusT = ENUM(ProcessStatus, name="process_status", create_type=False)


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, insert_default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), insert_default=now_with_tz, nullable=False)


class Agent(Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(VARCHAR(124), nullable=False)
    description: Mapped[str | None] = mapped_column(VARCHAR(512), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, insert_default=True)
    is_default_recipient: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, insert_default=False)


class Document(Base):
    __tablename__ = "documents"

    name: Mapped[str] = mapped_column(VARCHAR(124), nullable=True)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", lazy="selectin"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    content: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1024), nullable=False)
    hash: Mapped[bytes] = mapped_column(BYTEA, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_chunks.id"), nullable=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Route(Base):
    __tablename__ = "routes"

    status: Mapped[ProcessStatus] = mapped_column(ProcessStatusT, nullable=False, insert_default=ProcessStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True, insert_default=None)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True, insert_default=None)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)


class Forwarded(Base):
    __tablename__ = "forwarded"

    purpose: Mapped[str | None] = mapped_column(VARCHAR(52), nullable=True)
    is_valid: Mapped[bool | None] = mapped_column(BOOLEAN, nullable=True, insert_default=None)
    is_hidden: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, insert_default=False)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    route_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=True)
    score: Mapped[float | None] = mapped_column(FLOAT, nullable=True)

    __table_args__ = (CheckConstraint("sender_id != recipient_id", name="ck_forwarded_sender_recipient_different"),)
