from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.lead_scoring import (
    LeadExplanationRequest,
    LeadExplanationResponse,
    LeadScoreDistributionResponse,
    LeadScoringRequest,
    LeadScoringResponse,
)
from app.services.lead_scoring import LeadQualificationEngine, LeadScoringConfigError

router = APIRouter(prefix="/lead-scoring", tags=["lead-scoring"])


@lru_cache(maxsize=1)
def get_lead_qualification_engine() -> LeadQualificationEngine:
    return LeadQualificationEngine.from_yaml(Path(settings.lead_scoring_config_path))


@router.post("/score", response_model=LeadScoringResponse)
async def score_lead(payload: LeadScoringRequest) -> LeadScoringResponse:
    try:
        return get_lead_qualification_engine().score(
            lead_information=payload.lead_information,
            buyer_information=payload.buyer_information,
        )
    except LeadScoringConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/distribution", response_model=LeadScoreDistributionResponse)
async def score_lead_distribution(payload: LeadScoringRequest) -> LeadScoreDistributionResponse:
    try:
        return get_lead_qualification_engine().distribution(
            lead_information=payload.lead_information,
            buyer_information=payload.buyer_information,
        )
    except LeadScoringConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post("/explain", response_model=LeadExplanationResponse)
async def explain_lead_score(payload: LeadExplanationRequest) -> LeadExplanationResponse:
    try:
        return get_lead_qualification_engine().explain(
            score=payload.score,
            lead_information=payload.lead_information,
            buyer_information=payload.buyer_information,
        )
    except LeadScoringConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
