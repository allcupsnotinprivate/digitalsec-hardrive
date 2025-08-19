from collections import defaultdict
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Depends, Query

from app.service_layer import A_AgentsService, ADocumentsService

from .schemas import (
    AgentIn,
    AgentOut,
    DocumentForward,
    DocumentForwardsOut,
    DocumentIn,
    DocumentOut,
    ForwardedIn,
    ForwardedOut,
)

router = APIRouter()


@router.post("/agents/register", status_code=201, response_model=AgentOut)
@inject
async def register_agent(data: AgentIn, agents_service: Injected[A_AgentsService] = Depends()) -> AgentOut:
    agent = await agents_service.register(name=data.name, description=data.description)
    return AgentOut(id=agent.id)


@router.post("/documents/admit", status_code=201, response_model=DocumentOut)
@inject
async def admit_document(data: DocumentIn, documents_service: Injected[ADocumentsService] = Depends()) -> DocumentOut:
    document = await documents_service.admit(name=data.name, content=data.content)
    return DocumentOut(id=document.id)


@router.post("/documents/forward", status_code=201, response_model=ForwardedOut)
@inject
async def forward_document(
    data: ForwardedIn, documents_service: Injected[ADocumentsService] = Depends()
) -> ForwardedOut:
    forwarded = await documents_service.forward(
        purpose=data.purpose,
        sender_id=data.sender_id,
        recipient_id=data.recipient_id,
        document_id=data.document_id,
        is_valid=True,
    )
    return ForwardedOut(id=forwarded.id)


@router.get("/documents/forwards/retrieve", status_code=200, response_model=DocumentForwardsOut)
@inject
async def retrieve_document_forwarded(
    document_id: UUID = Query(alias="documentId"), documents_service: Injected[ADocumentsService] = Depends()
) -> DocumentForwardsOut:
    forwarded_seq = await documents_service.retrieve_forwards(id=document_id, sender_id=None)

    grouped: dict[UUID, set[UUID]] = defaultdict(set)
    for fwd in forwarded_seq:
        if fwd.sender_id:
            grouped[fwd.sender_id].add(fwd.recipient_id)

    if not grouped:
        return DocumentForwardsOut(forwards=[])

    forwards = [
        DocumentForward(sender_id=sender, recipient_ids=list(recipients)) for sender, recipients in grouped.items()
    ]

    return DocumentForwardsOut(forwards=forwards)
