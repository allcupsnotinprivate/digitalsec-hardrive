from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, status

from app.infrastructure import ARabbitMQ
from app.infrastructure.rabbitmq import INVESTIGATION_QUEUE
from app.models import ProcessStatus
from app.service_layer import ARoutesService

from .schemas import ForwardedOut, RouteDocumentIn, RouteDocumentOut, RouteInvestigationIn, RouteInvestigationOut

router = APIRouter()


@router.post("/initialize", status_code=201, response_model=RouteDocumentOut)
@inject
async def initialize_routing(
    data: RouteDocumentIn, routes_service: Injected[ARoutesService] = Depends()
) -> RouteDocumentOut:
    route = await routes_service.initialize(document_id=data.document_id, sender_id=data.sender_id)
    return RouteDocumentOut(
        id=route.id, status=route.status, started_at=route.started_at, completed_at=route.completed_at
    )


@router.get("/retrieve", status_code=200, response_model=RouteDocumentOut)
@inject
async def retrieve_route(id: UUID = Query(), routes_service: Injected[ARoutesService] = Depends()) -> RouteDocumentOut:
    route = await routes_service.retrieve(id=id)
    return RouteDocumentOut(
        id=route.id, status=route.status, started_at=route.started_at, completed_at=route.completed_at
    )


@router.post("/investigate", status_code=202)
@inject
async def investigate_routing(
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    route_id: UUID = Query(alias="routeId"),
    data: RouteInvestigationIn = Body(),
    routes_service: Injected[ARoutesService] = Depends(),
    rabbitmq: Injected[ARabbitMQ] = Depends(),
) -> None:
    route = await routes_service.retrieve(id=route_id)

    if route.status != ProcessStatus.PENDING and not (
        data.allow_recovery and route.status in (ProcessStatus.FAILED, ProcessStatus.TIMEOUT)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Route investigation completed with status {route.status.value}",
        )

    headers: dict[str, str] = {}
    if x_request_id:
        headers["X-Request-ID"] = x_request_id

    await rabbitmq.publish_message(
        INVESTIGATION_QUEUE,
        {"route_id": str(route_id), "allow_recovery": data.allow_recovery},
        headers=headers or None,
    )


@router.post("/cancel", status_code=200, response_model=RouteDocumentOut)
@inject
async def cancel_route(
    route_id: UUID = Query(alias="routeId"), routes_service: Injected[ARoutesService] = Depends()
) -> RouteDocumentOut:
    route = await routes_service.cancel(id=route_id)

    return RouteDocumentOut(
        id=route.id,
        status=route.status,
        started_at=route.started_at,
        completed_at=route.completed_at,
    )


@router.get("/investigations/forwards/fetch", status_code=200, response_model=RouteInvestigationOut)
@inject
async def retrieve_investigation_results(
    route_id: UUID = Query(alias="routeId"), routes_service: Injected[ARoutesService] = Depends()
) -> RouteInvestigationOut:
    route, forwards = await routes_service.fetch(id=route_id)
    result = RouteInvestigationOut(
        status=route.status,
        forwards=[
            ForwardedOut(
                sender_id=forwarded.sender_id,
                recipient_id=forwarded.recipient_id,
                score=round(forwarded.score, 4) if forwarded.score else forwarded.score,
            )
            for forwarded in forwards
        ],
    )
    return result
