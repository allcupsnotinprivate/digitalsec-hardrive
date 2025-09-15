from collections import defaultdict
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Depends, Query

from app.api.rest.schemas import PaginationParams, build_page_info
from app.service_layer import A_AgentsService, ADocumentsService, ARoutesService

from .schemas import (
    AgentIn,
    AgentOut,
    AgentSearchFilters,
    AgentSearchResponse,
    DocumentForward,
    DocumentForwardsOut,
    DocumentIn,
    DocumentOut,
    ForwardedIn,
    ForwardedOut,
    AgentRead,
    DocumentSearchResponse,
    DocumentSearchFilters,
    DocumentRead,
    DocumentChunkSearchResponse,
    DocumentChunkSearchFilters,
    DocumentChunkRead,
    ForwardedSearchResponse,
    ForwardedSearchFilters,
    ForwardedRead,
    RouteSearchFilters,
    RouteSearchResponse,
    RouteRead,
)

router = APIRouter()


@router.post("/agents/register", status_code=201, response_model=AgentOut)
@inject
async def register_agent(data: AgentIn, agents_service: Injected[A_AgentsService] = Depends()) -> AgentOut:
    agent = await agents_service.register(
        name=data.name, description=data.description, is_default_recipient=data.is_default_recipient
    )
    return AgentOut(id=agent.id)


@router.get("/agents/search", response_model=AgentSearchResponse, status_code=200)
@inject
async def search_agents(
    pagination: PaginationParams = Depends(),
    filters: AgentSearchFilters = Depends(),
    agents_service: Injected[A_AgentsService] = Depends(),
) -> AgentSearchResponse:
    agents, total = await agents_service.search(
        page=pagination.page,
        page_size=pagination.page_size,
        name=filters.name,
        description=filters.description,
        is_active=filters.is_active,
        is_default_recipient=filters.is_default_recipient,
    )

    return AgentSearchResponse(
        items=[
            AgentRead(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                is_active=agent.is_active,
                is_default_recipient=agent.is_default_recipient,
                created_at=agent.created_at,
            )
            for agent in agents
        ],
        pageInfo=build_page_info(total=total, page=pagination.page, page_size=pagination.page_size),
    )


@router.post("/documents/admit", status_code=201, response_model=DocumentOut)
@inject
async def admit_document(data: DocumentIn, documents_service: Injected[ADocumentsService] = Depends()) -> DocumentOut:
    document = await documents_service.admit(name=data.name, content=data.content)
    return DocumentOut(id=document.id)


@router.get("/documents/search", response_model=DocumentSearchResponse, status_code=200)
@inject
async def search_documents(
    pagination: PaginationParams = Depends(),
    filters: DocumentSearchFilters = Depends(),
    documents_service: Injected[ADocumentsService] = Depends(),
) -> DocumentSearchResponse:
    documents, total = await documents_service.search(
        page=pagination.page,
        page_size=pagination.page_size,
        name=filters.name,
        created_from=filters.created_from,
        created_to=filters.created_to,
    )

    return DocumentSearchResponse(
        items=[
            DocumentRead(id=document.id, name=document.name, created_at=document.created_at)
            for document in documents
        ],
        pageInfo=build_page_info(total=total, page=pagination.page, page_size=pagination.page_size),
    )


@router.get("/documents/chunks/search", response_model=DocumentChunkSearchResponse, status_code=200)
@inject
async def search_document_chunks(
    pagination: PaginationParams = Depends(),
    filters: DocumentChunkSearchFilters = Depends(),
    documents_service: Injected[ADocumentsService] = Depends(),
) -> DocumentChunkSearchResponse:
    chunks, total = await documents_service.search_chunks(
        page=pagination.page,
        page_size=pagination.page_size,
        document_id=filters.document_id,
        parent_id=filters.parent_id,
        content=filters.content,
    )

    return DocumentChunkSearchResponse(
        items=[
            DocumentChunkRead(
                id=chunk.id,
                documentId=chunk.document_id,
                parentId=chunk.parent_id,
                content=chunk.content,
                created_at=chunk.created_at,
            )
            for chunk in chunks
        ],
        pageInfo=build_page_info(total=total, page=pagination.page, page_size=pagination.page_size),
    )


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


@router.get("/forwards/search", response_model=ForwardedSearchResponse, status_code=200)
@inject
async def search_forwarded(
    pagination: PaginationParams = Depends(),
    filters: ForwardedSearchFilters = Depends(),
    documents_service: Injected[ADocumentsService] = Depends(),
) -> ForwardedSearchResponse:
    forwarded_seq, total = await documents_service.search_forwarded(
        page=pagination.page,
        page_size=pagination.page_size,
        document_id=filters.document_id,
        sender_id=filters.sender_id,
        recipient_id=filters.recipient_id,
        route_id=filters.route_id,
        is_valid=filters.is_valid,
        is_hidden=filters.is_hidden,
        purpose=filters.purpose,
    )

    return ForwardedSearchResponse(
        items=[
            ForwardedRead(
                id=forwarded.id,
                documentId=forwarded.document_id,
                senderId=forwarded.sender_id,
                recipientId=forwarded.recipient_id,
                routeId=forwarded.route_id,
                purpose=forwarded.purpose,
                isValid=forwarded.is_valid,
                isHidden=forwarded.is_hidden,
                score=forwarded.score,
                created_at=forwarded.created_at,
            )
            for forwarded in forwarded_seq
        ],
        pageInfo=build_page_info(total=total, page=pagination.page, page_size=pagination.page_size),
    )


@router.get("/routes/search", response_model=RouteSearchResponse, status_code=200)
@inject
async def search_routes(
    pagination: PaginationParams = Depends(),
    filters: RouteSearchFilters = Depends(),
    routes_service: Injected[ARoutesService] = Depends(),
) -> RouteSearchResponse:
    routes, total = await routes_service.search(
        page=pagination.page,
        page_size=pagination.page_size,
        document_id=filters.document_id,
        sender_id=filters.sender_id,
        status=filters.status,
        started_from=filters.started_from,
        started_to=filters.started_to,
        completed_from=filters.completed_from,
        completed_to=filters.completed_to,
    )

    return RouteSearchResponse(
        items=[
            RouteRead(
                id=route.id,
                documentId=route.document_id,
                senderId=route.sender_id,
                status=route.status,
                startedAt=route.started_at,
                completedAt=route.completed_at,
                createdAt=route.created_at,
            )
            for route in routes
        ],
        pageInfo=build_page_info(total=total, page=pagination.page, page_size=pagination.page_size),
    )
