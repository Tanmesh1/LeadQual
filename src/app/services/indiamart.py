from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

from app.models.lead import IndiaMartLead
from app.repositories.indiamart import IndiaMartLeadRepository
from app.schemas.indiamart import (
    IndiaMartLeadBatchCreate,
    IndiaMartLeadCreate,
    IndiaMartLeadFilters,
)
from app.services.lead_scoring import LeadQualificationEngine, LeadScoringConfigError


class IndiaMartLeadServiceError(Exception):
    """Base IndiaMART lead service exception."""


class IndiaMartLeadPersistenceError(IndiaMartLeadServiceError):
    pass


class IndiaMartLeadScoringError(IndiaMartLeadServiceError):
    pass


@dataclass(frozen=True)
class IndiaMartLeadListResult:
    items: list[IndiaMartLead]
    total: int
    page: int
    size: int


@dataclass(frozen=True)
class IndiaMartLeadBatchResult:
    items: list[IndiaMartLead]
    created: int
    updated: int


class IndiaMartLeadService:
    def __init__(
        self,
        repository: IndiaMartLeadRepository,
        scoring_engine: LeadQualificationEngine,
    ) -> None:
        self.repository = repository
        self.scoring_engine = scoring_engine

    async def upsert_lead(self, payload: IndiaMartLeadCreate) -> tuple[IndiaMartLead, bool]:
        lead = IndiaMartLead(**payload.model_dump(mode="python"))
        try:
            self._score_extracted_lead(lead)
        except LeadScoringConfigError as exc:
            raise IndiaMartLeadScoringError("Unable to score IndiaMART lead") from exc

        try:
            return await self.repository.upsert(lead)
        except SQLAlchemyError as exc:
            await self.repository.session.rollback()
            raise IndiaMartLeadPersistenceError("Unable to persist IndiaMART lead") from exc

    async def upsert_batch(self, payload: IndiaMartLeadBatchCreate) -> IndiaMartLeadBatchResult:
        created = 0
        updated = 0
        items: list[IndiaMartLead] = []

        for item in payload.items:
            lead, was_created = await self.upsert_lead(item)
            items.append(lead)
            if was_created:
                created += 1
            else:
                updated += 1

        return IndiaMartLeadBatchResult(items=items, created=created, updated=updated)

    async def list_leads(self, filters: IndiaMartLeadFilters) -> IndiaMartLeadListResult:
        try:
            items, total = await self.repository.list(filters)
        except SQLAlchemyError as exc:
            raise IndiaMartLeadPersistenceError("Unable to list IndiaMART leads") from exc

        return IndiaMartLeadListResult(
            items=list(items),
            total=total,
            page=filters.page,
            size=filters.size,
        )

    async def delete_all_leads(self) -> int:
        try:
            return await self.repository.delete_all()
        except SQLAlchemyError as exc:
            await self.repository.session.rollback()
            raise IndiaMartLeadPersistenceError("Unable to delete IndiaMART leads") from exc

    def _score_extracted_lead(self, lead: IndiaMartLead) -> None:
        lead_information = self._build_lead_information(lead)
        buyer_information = self._build_buyer_information(lead)
        score_result = self.scoring_engine.score(
            lead_information=lead_information,
            buyer_information=buyer_information,
        )
        explanation = self.scoring_engine.explain(
            score=score_result.score,
            lead_information=lead_information,
            buyer_information=buyer_information,
        )

        lead.lead_score_value = score_result.score
        lead.lead_score_category = score_result.category
        lead.lead_score_reasons = score_result.reasons
        lead.lead_score_explanation = explanation.model_dump(mode="json")
        lead.lead_scored_at = datetime.now(UTC)

    @staticmethod
    def _build_lead_information(lead: IndiaMartLead) -> dict[str, object]:
        return {
            "source": "indiamart",
            "phone": "available" if lead.phone_available else None,
            "product_name": lead.product_name,
            "product_category": lead.product_category,
            "purpose": lead.purpose,
            "lead_time": lead.lead_time,
            "requirements_count": lead.requirements_count,
            "replies_count": lead.replies_count,
        }

    @staticmethod
    def _build_buyer_information(lead: IndiaMartLead) -> dict[str, object]:
        return {
            "company_name": lead.business_name,
            "buyer_name": lead.buyer_name,
            "industry": lead.product_category,
            "country": "India",
            "city": lead.city,
            "state": lead.state,
            "years_active": lead.years_active,
            "business_available": lead.business_available,
            "address_available": lead.address_available,
        }
