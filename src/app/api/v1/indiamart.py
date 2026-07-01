from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.lead_scoring import get_lead_qualification_engine
from app.dependencies.database import get_database_session
from app.repositories.indiamart import IndiaMartLeadRepository
from app.schemas.indiamart import (
    IndiaMartLeadBatchCreate,
    IndiaMartLeadBatchResponse,
    IndiaMartLeadCreate,
    IndiaMartLeadDeleteAllResponse,
    IndiaMartLeadFilters,
    IndiaMartLeadListResponse,
    IndiaMartLeadRead,
)
from app.services.indiamart import (
    IndiaMartLeadPersistenceError,
    IndiaMartLeadScoringError,
    IndiaMartLeadService,
)

router = APIRouter(prefix="/indiamart/leads", tags=["indiamart"])


def get_indiamart_lead_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> IndiaMartLeadService:
    return IndiaMartLeadService(
        IndiaMartLeadRepository(session),
        get_lead_qualification_engine(),
    )


@router.post("", response_model=IndiaMartLeadRead, status_code=status.HTTP_201_CREATED)
async def upsert_indiamart_lead(
    payload: IndiaMartLeadCreate,
    service: Annotated[IndiaMartLeadService, Depends(get_indiamart_lead_service)],
) -> IndiaMartLeadRead:
    try:
        lead, _ = await service.upsert_lead(payload)
        return lead
    except IndiaMartLeadScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to score IndiaMART lead",
        ) from exc
    except IndiaMartLeadPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to persist IndiaMART lead",
        ) from exc


@router.post("/batch", response_model=IndiaMartLeadBatchResponse)
async def upsert_indiamart_leads_batch(
    payload: IndiaMartLeadBatchCreate,
    service: Annotated[IndiaMartLeadService, Depends(get_indiamart_lead_service)],
) -> IndiaMartLeadBatchResponse:
    try:
        result = await service.upsert_batch(payload)
    except IndiaMartLeadScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to score IndiaMART leads",
        ) from exc
    except IndiaMartLeadPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to persist IndiaMART leads",
        ) from exc

    return IndiaMartLeadBatchResponse(
        items=result.items,
        created=result.created,
        updated=result.updated,
    )


@router.delete("", response_model=IndiaMartLeadDeleteAllResponse)
async def delete_all_indiamart_leads(
    service: Annotated[IndiaMartLeadService, Depends(get_indiamart_lead_service)],
) -> IndiaMartLeadDeleteAllResponse:
    try:
        deleted = await service.delete_all_leads()
    except IndiaMartLeadPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete IndiaMART leads",
        ) from exc

    return IndiaMartLeadDeleteAllResponse(deleted=deleted)


@router.get("", response_model=IndiaMartLeadListResponse)
async def list_indiamart_leads(
    service: Annotated[IndiaMartLeadService, Depends(get_indiamart_lead_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    product_name: Annotated[str | None, Query(max_length=255)] = None,
    buyer_name: Annotated[str | None, Query(max_length=255)] = None,
    business_name: Annotated[str | None, Query(max_length=255)] = None,
    city: Annotated[str | None, Query(max_length=100)] = None,
    state: Annotated[str | None, Query(max_length=100)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    sort_by: Annotated[
        str,
        Query(pattern="^(extracted_at|product_name|buyer_name|business_name|city)$"),
    ] = "extracted_at",
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> IndiaMartLeadListResponse:
    filters = IndiaMartLeadFilters(
        page=page,
        size=size,
        product_name=product_name,
        buyer_name=buyer_name,
        business_name=business_name,
        city=city,
        state=state,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    try:
        result = await service.list_leads(filters)
    except IndiaMartLeadPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to list IndiaMART leads",
        ) from exc

    return IndiaMartLeadListResponse.create(
        items=result.items,
        total=result.total,
        page=result.page,
        size=result.size,
    )
