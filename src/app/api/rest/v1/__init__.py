from fastapi import APIRouter

from .intakes import router as intake_router
from .routes import router as routes_router

router = APIRouter()
router.include_router(intake_router, prefix="/intakes", tags=["Intakes"])
router.include_router(routes_router, prefix="/routes", tags=["Routes"])

__all__ = ["router"]
