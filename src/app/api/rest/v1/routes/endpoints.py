from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Body, Depends, Query

from app.service_layer import ARoutesService
from app.tasks.routes import investigate_route

from .schemas import ForwardedOut, RouteDocumentIn, RouteDocumentOut, RouteInvestigationIn, RouteInvestigationOut

router = APIRouter()


@router.post("/initialize", status_code=201, response_model=RouteDocumentOut)
@inject
async def initialize_routing(
    data: RouteDocumentIn, routes_service: Injected[ARoutesService] = Depends()
) -> RouteDocumentOut:
    route = await routes_service.initialize(document_id=data.document_id)
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
    route_id: UUID = Query(alias="routeId"),
    data: RouteInvestigationIn = Body(),
) -> None:
    investigate_route.delay(
        str(route_id),
        str(data.sender_id) if data.sender_id else None,
        allow_recovery=data.allow_recovery,
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
            ForwardedOut(sender_id=forwarded.sender_id, recipient_id=forwarded.recipient_id) for forwarded in forwards
        ],
    )
    return result
