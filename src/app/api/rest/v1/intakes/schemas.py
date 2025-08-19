from uuid import UUID

from pydantic import Field

from app.utils.hash import create_document_name
from app.utils.schemas import BaseAPISchema


class DocumentIn(BaseAPISchema):
    name: str = Field(default_factory=create_document_name)
    content: str = Field()


class DocumentOut(BaseAPISchema):
    id: UUID = Field()


class AgentIn(BaseAPISchema):
    name: str = Field()
    description: str | None = Field()


class AgentOut(BaseAPISchema):
    id: UUID = Field()


class ForwardedIn(BaseAPISchema):
    purpose: str | None = Field()
    sender_id: UUID = Field()
    recipient_id: UUID = Field()
    document_id: UUID = Field()


class ForwardedOut(BaseAPISchema):
    id: UUID = Field()


class DocumentForward(BaseAPISchema):
    sender_id: UUID = Field()
    recipient_ids: list[UUID] = Field()


class DocumentForwardsOut(BaseAPISchema):
    forwards: list[DocumentForward] = Field()
