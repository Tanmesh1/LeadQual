from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.indiamart import router as indiamart_router
from app.api.v1.lead_scoring import router as lead_scoring_router
from app.api.v1.leads import router as leads_router
from app.api.v1.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(leads_router)
api_router.include_router(indiamart_router)
api_router.include_router(lead_scoring_router)
api_router.include_router(reports_router)
