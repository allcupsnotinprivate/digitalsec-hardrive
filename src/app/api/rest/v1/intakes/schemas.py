from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.rest.schemas import PageMeta
from app.models import ProcessStatus
from app.utils.hash import create_document_name
from app.utils.schemas import BaseAPISchema


class DocumentIn(BaseAPISchema):
    name: str = Field(default_factory=create_document_name)
    content: str = Field()


class DocumentOut(BaseAPISchema):
    id: UUID = Field()


class DocumentSearchFilters(BaseAPISchema):
    name: str | None = Field(default=None)
    created_from: datetime | None = Field(default=None, alias="createdFrom")
    created_to: datetime | None = Field(default=None, alias="createdTo")


class DocumentRead(BaseAPISchema):
    id: UUID = Field()
    name: str | None = Field(default=None)
    created_at: datetime = Field()


class DocumentSearchResponse(BaseAPISchema):
    items: list[DocumentRead] = Field(default_factory=list)
    page_info: PageMeta = Field(alias="pageInfo")


class DocumentChunkSearchFilters(BaseAPISchema):
    document_id: UUID | None = Field(default=None, alias="documentId")
    parent_id: UUID | None = Field(default=None, alias="parentId")
    content: str | None = Field(default=None)


class DocumentChunkRead(BaseAPISchema):
    id: UUID = Field()
    document_id: UUID = Field(alias="documentId")
    parent_id: UUID | None = Field(default=None, alias="parentId")
    content: str = Field()
    created_at: datetime = Field()


class DocumentChunkSearchResponse(BaseAPISchema):
    items: list[DocumentChunkRead] = Field(default_factory=list)
    page_info: PageMeta = Field(alias="pageInfo")


class AgentIn(BaseAPISchema):
    name: str = Field()
    description: str | None = Field()
    is_default_recipient: bool = Field(default=False)


class AgentOut(BaseAPISchema):
    id: UUID = Field()


class AgentSearchFilters(BaseAPISchema):
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    is_default_recipient: bool | None = Field(default=None)


class AgentRead(BaseAPISchema):
    id: UUID = Field()
    name: str = Field()
    description: str | None = Field(default=None)
    is_active: bool = Field()
    is_default_recipient: bool = Field()
    created_at: datetime = Field()


class AgentSearchResponse(BaseAPISchema):
    items: list[AgentRead] = Field(default_factory=list)
    page_info: PageMeta = Field(alias="pageInfo")


class ForwardedIn(BaseAPISchema):
    purpose: str | None = Field()
    sender_id: UUID = Field()
    recipient_id: UUID = Field()
    document_id: UUID = Field()


class ForwardedOut(BaseAPISchema):
    id: UUID = Field()


class ForwardedSearchFilters(BaseAPISchema):
    document_id: UUID | None = Field(default=None, alias="documentId")
    sender_id: UUID | None = Field(default=None, alias="senderId")
    recipient_id: UUID | None = Field(default=None, alias="recipientId")
    route_id: UUID | None = Field(default=None, alias="routeId")
    is_valid: bool | None = Field(default=None, alias="isValid")
    is_hidden: bool | None = Field(default=None, alias="isHidden")
    purpose: str | None = Field(default=None)


class ForwardedRead(BaseAPISchema):
    id: UUID = Field()
    document_id: UUID = Field(alias="documentId")
    sender_id: UUID | None = Field(default=None, alias="senderId")
    recipient_id: UUID = Field(alias="recipientId")
    route_id: UUID | None = Field(default=None, alias="routeId")
    purpose: str | None = Field(default=None)
    is_valid: bool | None = Field(default=None, alias="isValid")
    is_hidden: bool = Field(alias="isHidden")
    score: float | None = Field(default=None)
    created_at: datetime = Field()


class ForwardedSearchResponse(BaseAPISchema):
    items: list[ForwardedRead] = Field(default_factory=list)
    page_info: PageMeta = Field(alias="pageInfo")


class DocumentForward(BaseAPISchema):
    sender_id: UUID = Field()
    recipient_ids: list[UUID] = Field()


class DocumentForwardsOut(BaseAPISchema):
    forwards: list[DocumentForward] = Field()


class RouteSearchFilters(BaseAPISchema):
    document_id: UUID | None = Field(default=None, alias="documentId")
    sender_id: UUID | None = Field(default=None, alias="senderId")
    status: ProcessStatus | None = Field(default=None)
    started_from: datetime | None = Field(default=None, alias="startedFrom")
    started_to: datetime | None = Field(default=None, alias="startedTo")
    completed_from: datetime | None = Field(default=None, alias="completedFrom")
    completed_to: datetime | None = Field(default=None, alias="completedTo")


class RouteRead(BaseAPISchema):
    id: UUID = Field()
    document_id: UUID = Field(alias="documentId")
    sender_id: UUID | None = Field(default=None, alias="senderId")
    status: ProcessStatus = Field()
    started_at: datetime | None = Field(default=None, alias="startedAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")
    created_at: datetime = Field(alias="createdAt")


class RouteSearchResponse(BaseAPISchema):
    items: list[RouteRead] = Field(default_factory=list)
    page_info: PageMeta = Field(alias="pageInfo")
