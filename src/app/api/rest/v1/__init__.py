from fastapi import APIRouter

from .analytics import router as analytics_router
from .intakes import router as intake_router
from .routes import router as routes_router

router = APIRouter()
router.include_router(intake_router, prefix="/intakes", tags=["Intakes"])
router.include_router(routes_router, prefix="/routes", tags=["Routes"])
router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])

__all__ = ["router"]
