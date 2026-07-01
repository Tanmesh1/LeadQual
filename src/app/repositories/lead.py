import uuid
from collections.abc import Sequence

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Buyer, Lead
from app.schemas.lead import LeadFilters


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, lead: Lead) -> Lead:
        self.session.add(lead)
        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    async def get_by_id(self, lead_id: uuid.UUID) -> Lead | None:
        result = await self.session.execute(select(Lead).where(Lead.id == lead_id))
        return result.scalar_one_or_none()

    async def buyer_exists(self, buyer_id: uuid.UUID) -> bool:
        result = await self.session.scalar(
            select(func.count()).select_from(Buyer).where(Buyer.id == buyer_id)
        )
        return bool(result)

    async def list(self, filters: LeadFilters) -> tuple[Sequence[Lead], int]:
        statement = self._apply_filters(select(Lead), filters)
        count_statement = self._apply_filters(select(func.count()).select_from(Lead), filters)

        total = await self.session.scalar(count_statement)
        statement = self._apply_sorting(statement, filters).offset(
            (filters.page - 1) * filters.size
        ).limit(filters.size)

        result = await self.session.execute(statement)
        return result.scalars().all(), total or 0

    async def update(self, lead: Lead, values: dict[str, object]) -> Lead:
        for field, value in values.items():
            setattr(lead, field, value)

        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    async def delete(self, lead: Lead) -> None:
        await self.session.execute(delete(Lead).where(Lead.id == lead.id))
        await self.session.commit()

    @staticmethod
    def _apply_filters(statement: Select, filters: LeadFilters) -> Select:
        if filters.buyer_id:
            statement = statement.where(Lead.buyer_id == filters.buyer_id)
        if filters.status:
            statement = statement.where(Lead.status == filters.status.value)
        if filters.source:
            statement = statement.where(Lead.source.ilike(f"%{filters.source}%"))
        if filters.company_name:
            statement = statement.where(Lead.company_name.ilike(f"%{filters.company_name}%"))
        if filters.email:
            statement = statement.where(Lead.email.ilike(f"%{filters.email}%"))
        if filters.search:
            pattern = f"%{filters.search}%"
            statement = statement.where(
                or_(
                    Lead.email.ilike(pattern),
                    Lead.first_name.ilike(pattern),
                    Lead.last_name.ilike(pattern),
                    Lead.company_name.ilike(pattern),
                    Lead.company_domain.ilike(pattern),
                    Lead.job_title.ilike(pattern),
                )
            )

        return statement

    @staticmethod
    def _apply_sorting(statement: Select, filters: LeadFilters) -> Select:
        sort_columns = {
            "created_at": Lead.created_at,
            "updated_at": Lead.updated_at,
            "email": Lead.email,
            "company_name": Lead.company_name,
            "status": Lead.status,
            "source": Lead.source,
        }
        column = sort_columns[filters.sort_by.value]
        return statement.order_by(column.asc() if filters.sort_order == "asc" else column.desc())
