import uuid
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1.leads import get_lead_service
from app.main import create_app
from app.services.lead import LeadConflictError, LeadListResult, LeadNotFoundError

BUYER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
LEAD_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def make_lead(**overrides: object) -> SimpleNamespace:
    values = {
        "id": LEAD_ID,
        "buyer_id": BUYER_ID,
        "email": "jane@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "job_title": "VP Sales",
        "phone": None,
        "linkedin_url": None,
        "source": "web",
        "status": "new",
        "company_name": "Example Inc",
        "company_domain": "example.com",
        "company_website_url": None,
        "company_industry": "Software",
        "company_employee_count": 42,
        "company_annual_revenue_usd": Decimal("1000000.00"),
        "country": "US",
        "region": "CA",
        "city": "San Francisco",
        "timezone": "America/Los_Angeles",
        "raw_payload": {},
        "created_at": datetime(2026, 6, 5, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 5, tzinfo=UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeLeadService:
    def __init__(self) -> None:
        self.created_payload = None
        self.list_filters = None
        self.updated_payload = None
        self.deleted_id = None
        self.raise_on_get = False
        self.raise_on_update = False

    async def create_lead(self, payload):
        self.created_payload = payload
        return make_lead(email=payload.email, buyer_id=payload.buyer_id)

    async def list_leads(self, filters):
        self.list_filters = filters
        return LeadListResult(items=[make_lead()], total=25, page=filters.page, size=filters.size)

    async def get_lead(self, lead_id):
        if self.raise_on_get:
            raise LeadNotFoundError("Lead not found")
        return make_lead(id=lead_id)

    async def update_lead(self, lead_id, payload):
        self.updated_payload = payload
        if self.raise_on_update:
            raise LeadConflictError("Conflict")
        return make_lead(id=lead_id, first_name=payload.first_name or "Jane")

    async def delete_lead(self, lead_id):
        self.deleted_id = lead_id


@pytest.fixture
def fake_service() -> FakeLeadService:
    return FakeLeadService()


@pytest.fixture
def client(fake_service: FakeLeadService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_lead_service] = lambda: fake_service
    return TestClient(app)


def test_create_lead(client: TestClient, fake_service: FakeLeadService) -> None:
    response = client.post(
        "/leads",
        json={
            "buyer_id": str(BUYER_ID),
            "email": "JANE@EXAMPLE.COM",
            "first_name": "Jane",
            "source": "web",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "jane@example.com"
    assert fake_service.created_payload.email == "jane@example.com"


def test_create_lead_validates_payload(client: TestClient) -> None:
    response = client.post(
        "/leads",
        json={
            "buyer_id": str(BUYER_ID),
            "email": "not-an-email",
            "company_employee_count": -1,
        },
    )

    assert response.status_code == 422


def test_list_leads_supports_pagination_filtering_and_sorting(
    client: TestClient,
    fake_service: FakeLeadService,
) -> None:
    response = client.get(
        "/leads",
        params={
            "page": 2,
            "size": 10,
            "status": "new",
            "source": "web",
            "search": "example",
            "sort_by": "email",
            "sort_order": "asc",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 25
    assert body["page"] == 2
    assert body["size"] == 10
    assert body["pages"] == 3
    assert fake_service.list_filters.status == "new"
    assert fake_service.list_filters.sort_by == "email"
    assert fake_service.list_filters.sort_order == "asc"


def test_get_lead_not_found(client: TestClient, fake_service: FakeLeadService) -> None:
    fake_service.raise_on_get = True

    response = client.get(f"/leads/{LEAD_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


def test_update_lead_conflict(client: TestClient, fake_service: FakeLeadService) -> None:
    fake_service.raise_on_update = True

    response = client.put(f"/leads/{LEAD_ID}", json={"email": "jane@example.com"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Lead already exists for this buyer and email"


def test_delete_lead(client: TestClient, fake_service: FakeLeadService) -> None:
    response = client.delete(f"/leads/{LEAD_ID}")

    assert response.status_code == 204
    assert fake_service.deleted_id == LEAD_ID
