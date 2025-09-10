from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models import ProcessStatus
from app.utils.schemas import BaseAPISchema


class RouteDocumentIn(BaseAPISchema):
    document_id: UUID = Field()


class RouteDocumentOut(BaseAPISchema):
    id: UUID = Field()
    status: ProcessStatus = Field()
    started_at: datetime | None = Field()
    completed_at: datetime | None = Field()


class RouteInvestigationIn(BaseAPISchema):
    sender_id: UUID | None = Field(default=None)
    allow_recovery: bool = Field(default=False)


class ForwardedOut(BaseAPISchema):
    sender_id: UUID | None
    recipient_id: UUID | None
    score: float | None


class RouteInvestigationOut(BaseAPISchema):
    status: ProcessStatus
    forwards: list[ForwardedOut] = Field(default=[])
