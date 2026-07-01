from collections.abc import Sequence

from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import IndiaMartLead
from app.schemas.indiamart import IndiaMartLeadFilters


class IndiaMartLeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, lead: IndiaMartLead) -> tuple[IndiaMartLead, bool]:
        existing = await self.get_by_fingerprint(lead.lead_fingerprint)
        if existing is None:
            self.session.add(lead)
            await self.session.commit()
            await self.session.refresh(lead)
            return lead, True

        values = {
            column.name: getattr(lead, column.name)
            for column in IndiaMartLead.__table__.columns
            if column.name not in {"id", "created_at", "updated_at"}
        }
        for field, value in values.items():
            setattr(existing, field, value)

        await self.session.commit()
        await self.session.refresh(existing)
        return existing, False

    async def get_by_fingerprint(self, fingerprint: str) -> IndiaMartLead | None:
        result = await self.session.execute(
            select(IndiaMartLead).where(IndiaMartLead.lead_fingerprint == fingerprint)
        )
        return result.scalar_one_or_none()

    async def list(self, filters: IndiaMartLeadFilters) -> tuple[Sequence[IndiaMartLead], int]:
        statement = self._apply_filters(select(IndiaMartLead), filters)
        count_statement = self._apply_filters(
            select(func.count()).select_from(IndiaMartLead),
            filters,
        )

        total = await self.session.scalar(count_statement)
        statement = self._apply_sorting(statement, filters).offset(
            (filters.page - 1) * filters.size
        ).limit(filters.size)

        result = await self.session.execute(statement)
        return result.scalars().all(), total or 0

    async def delete_all(self) -> int:
        result = await self.session.execute(delete(IndiaMartLead))
        await self.session.commit()
        return result.rowcount or 0

    @staticmethod
    def _apply_filters(statement: Select, filters: IndiaMartLeadFilters) -> Select:
        if filters.product_name:
            statement = statement.where(
                IndiaMartLead.product_name.ilike(f"%{filters.product_name}%")
            )
        if filters.buyer_name:
            statement = statement.where(IndiaMartLead.buyer_name.ilike(f"%{filters.buyer_name}%"))
        if filters.business_name:
            statement = statement.where(
                IndiaMartLead.business_name.ilike(f"%{filters.business_name}%")
            )
        if filters.city:
            statement = statement.where(IndiaMartLead.city.ilike(f"%{filters.city}%"))
        if filters.state:
            statement = statement.where(IndiaMartLead.state.ilike(f"%{filters.state}%"))
        if filters.search:
            pattern = f"%{filters.search}%"
            statement = statement.where(
                or_(
                    IndiaMartLead.product_name.ilike(pattern),
                    IndiaMartLead.product_category.ilike(pattern),
                    IndiaMartLead.buyer_name.ilike(pattern),
                    IndiaMartLead.business_name.ilike(pattern),
                    IndiaMartLead.city.ilike(pattern),
                    IndiaMartLead.state.ilike(pattern),
                )
            )
        return statement

    @staticmethod
    def _apply_sorting(statement: Select, filters: IndiaMartLeadFilters) -> Select:
        sort_columns = {
            "extracted_at": IndiaMartLead.extracted_at,
            "product_name": IndiaMartLead.product_name,
            "buyer_name": IndiaMartLead.buyer_name,
            "business_name": IndiaMartLead.business_name,
            "city": IndiaMartLead.city,
        }
        column = sort_columns[filters.sort_by]
        return statement.order_by(column.asc() if filters.sort_order == "asc" else column.desc())
