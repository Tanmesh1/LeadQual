import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_database_session
from app.repositories.lead import LeadRepository
from app.schemas.lead import (
    LeadCreate,
    LeadFilters,
    LeadListResponse,
    LeadRead,
    LeadSortField,
    LeadStatus,
    LeadUpdate,
)
from app.services.lead import (
    LeadBuyerNotFoundError,
    LeadConflictError,
    LeadNotFoundError,
    LeadPersistenceError,
    LeadService,
)

router = APIRouter(prefix="/leads", tags=["leads"])


def get_lead_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LeadService:
    return LeadService(LeadRepository(session))


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    service: Annotated[LeadService, Depends(get_lead_service)],
) -> LeadRead:
    try:
        return await service.create_lead(payload)
    except LeadBuyerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Buyer not found",
        ) from exc
    except LeadConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lead already exists for this buyer and email",
        ) from exc
    except LeadPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create lead",
        ) from exc


@router.get("", response_model=LeadListResponse)
async def list_leads(
    service: Annotated[LeadService, Depends(get_lead_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    buyer_id: uuid.UUID | None = None,
    lead_status: Annotated[LeadStatus | None, Query(alias="status")] = None,
    source: Annotated[str | None, Query(max_length=100)] = None,
    company_name: Annotated[str | None, Query(max_length=255)] = None,
    email: Annotated[str | None, Query(max_length=320)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    sort_by: LeadSortField = LeadSortField.CREATED_AT,
    sort_order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> LeadListResponse:
    filters = LeadFilters(
        page=page,
        size=size,
        buyer_id=buyer_id,
        status=lead_status,
        source=source,
        company_name=company_name,
        email=email,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    try:
        result = await service.list_leads(filters)
    except LeadPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to list leads",
        ) from exc

    return LeadListResponse.create(
        items=result.items,
        total=result.total,
        page=result.page,
        size=result.size,
    )


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(
    lead_id: uuid.UUID,
    service: Annotated[LeadService, Depends(get_lead_service)],
) -> LeadRead:
    try:
        return await service.get_lead(lead_id)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found") from exc


@router.put("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    service: Annotated[LeadService, Depends(get_lead_service)],
) -> LeadRead:
    try:
        return await service.update_lead(lead_id, payload)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found") from exc
    except LeadBuyerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Buyer not found",
        ) from exc
    except LeadConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Lead already exists for this buyer and email",
        ) from exc
    except LeadPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update lead",
        ) from exc


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: uuid.UUID,
    service: Annotated[LeadService, Depends(get_lead_service)],
) -> Response:
    try:
        await service.delete_lead(lead_id)
    except LeadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found") from exc
    except LeadPersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete lead",
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
