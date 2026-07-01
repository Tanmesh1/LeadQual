import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.lead import Lead
from app.repositories.lead import LeadRepository
from app.schemas.lead import LeadCreate, LeadFilters, LeadUpdate


class LeadServiceError(Exception):
    """Base lead service exception."""


class LeadNotFoundError(LeadServiceError):
    pass


class LeadBuyerNotFoundError(LeadServiceError):
    pass


class LeadConflictError(LeadServiceError):
    pass


class LeadPersistenceError(LeadServiceError):
    pass


@dataclass(frozen=True)
class LeadListResult:
    items: list[Lead]
    total: int
    page: int
    size: int


class LeadService:
    def __init__(self, repository: LeadRepository) -> None:
        self.repository = repository

    async def create_lead(self, payload: LeadCreate) -> Lead:
        if not await self.repository.buyer_exists(payload.buyer_id):
            raise LeadBuyerNotFoundError("Buyer not found")

        lead = Lead(**payload.model_dump(mode="python"))
        try:
            return await self.repository.create(lead)
        except IntegrityError as exc:
            await self.repository.session.rollback()
            raise LeadConflictError("Lead already exists for this buyer and email") from exc
        except SQLAlchemyError as exc:
            await self.repository.session.rollback()
            raise LeadPersistenceError("Unable to create lead") from exc

    async def list_leads(self, filters: LeadFilters) -> LeadListResult:
        try:
            items, total = await self.repository.list(filters)
        except SQLAlchemyError as exc:
            raise LeadPersistenceError("Unable to list leads") from exc

        return LeadListResult(
            items=list(items),
            total=total,
            page=filters.page,
            size=filters.size,
        )

    async def get_lead(self, lead_id: uuid.UUID) -> Lead:
        lead = await self.repository.get_by_id(lead_id)
        if lead is None:
            raise LeadNotFoundError("Lead not found")
        return lead

    async def update_lead(self, lead_id: uuid.UUID, payload: LeadUpdate) -> Lead:
        lead = await self.get_lead(lead_id)
        values = payload.model_dump(exclude_unset=True, mode="python")

        if not values:
            return lead

        buyer_id = values.get("buyer_id")
        if isinstance(buyer_id, uuid.UUID) and not await self.repository.buyer_exists(buyer_id):
            raise LeadBuyerNotFoundError("Buyer not found")

        try:
            return await self.repository.update(lead, values)
        except IntegrityError as exc:
            await self.repository.session.rollback()
            raise LeadConflictError("Lead already exists for this buyer and email") from exc
        except SQLAlchemyError as exc:
            await self.repository.session.rollback()
            raise LeadPersistenceError("Unable to update lead") from exc

    async def delete_lead(self, lead_id: uuid.UUID) -> None:
        lead = await self.get_lead(lead_id)
        try:
            await self.repository.delete(lead)
        except SQLAlchemyError as exc:
            await self.repository.session.rollback()
            raise LeadPersistenceError("Unable to delete lead") from exc
