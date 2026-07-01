from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.reports.excel_report import LeadReportRow


@dataclass(frozen=True)
class LeadSummary:
    report_date: date
    total_leads: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    conversion_rate: float
    top_product: str
    top_opportunity_name: str
    top_opportunity_score: int
    estimated_revenue: Decimal

    def as_plain_text(self) -> str:
        return (
            "Lead Intelligence Summary\n\n"
            f"{self.total_leads} leads received today.\n\n"
            f"{self.hot_leads} Hot Leads identified.\n\n"
            f"{self.top_product} generated the highest lead volume.\n\n"
            "Top opportunity:\n"
            f"{self.top_opportunity_name} with "
            f"{self.top_opportunity_score}% qualification score.\n\n"
            "Estimated potential revenue:\n"
            f"Rs. {self.estimated_revenue:,.0f}."
        )

    def as_email_html(self) -> str:
        return (
            "<h2>Lead Intelligence Summary</h2>"
            "<ul>"
            f"<li><strong>Total Leads:</strong> {self.total_leads}</li>"
            f"<li><strong>Hot Leads:</strong> {self.hot_leads}</li>"
            f"<li><strong>Warm Leads:</strong> {self.warm_leads}</li>"
            f"<li><strong>Cold Leads:</strong> {self.cold_leads}</li>"
            f"<li><strong>Conversion Rate:</strong> {self.conversion_rate:.2f}%</li>"
            "</ul>"
            f"<p><strong>Top Opportunity:</strong> {self.top_opportunity_name}</p>"
            "<p><strong>Estimated Potential Revenue:</strong> "
            f"Rs. {self.estimated_revenue:,.0f}</p>"
            "<p>The complete report is attached.</p>"
        )

    def as_telegram_text(self) -> str:
        return (
            "Lead Intelligence Report\n\n"
            f"Date: {self.report_date.isoformat()}\n\n"
            f"Total Leads: {self.total_leads}\n"
            f"Hot Leads: {self.hot_leads}\n"
            f"Warm Leads: {self.warm_leads}\n"
            f"Cold Leads: {self.cold_leads}\n\n"
            "Top Opportunity:\n"
            f"{self.top_opportunity_name}\n\n"
            "Excel report attached."
        )


class SummaryGenerator:
    def generate(
        self,
        leads: list[LeadReportRow],
        *,
        report_date: date | None = None,
    ) -> LeadSummary:
        total = len(leads)
        category_counts = Counter(lead.lead_category for lead in leads)
        converted = sum(1 for lead in leads if lead.converted)
        top_product = self._top_product(leads)
        top_opportunity = max(leads, key=lambda lead: lead.qualification_score, default=None)
        revenue = sum((lead.order_value for lead in leads), Decimal("0"))

        return LeadSummary(
            report_date=report_date or date.today(),
            total_leads=total,
            hot_leads=category_counts["HOT"],
            warm_leads=category_counts["WARM"],
            cold_leads=category_counts["COLD"],
            conversion_rate=(converted / total * 100) if total else 0,
            top_product=top_product,
            top_opportunity_name=top_opportunity.business_name if top_opportunity else "N/A",
            top_opportunity_score=top_opportunity.qualification_score if top_opportunity else 0,
            estimated_revenue=revenue,
        )

    @staticmethod
    def _top_product(leads: list[LeadReportRow]) -> str:
        if not leads:
            return "N/A"
        product_counts = Counter(lead.product_name for lead in leads)
        return product_counts.most_common(1)[0][0]
