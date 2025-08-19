from fastapi import APIRouter

from .endpoints import router as router_

router = APIRouter()

router.include_router(router_)

__all__ = ["router"]
