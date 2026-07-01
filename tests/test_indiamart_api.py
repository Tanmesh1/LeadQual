import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1.indiamart import get_indiamart_lead_service
from app.main import create_app
from app.schemas.indiamart import IndiaMartLeadCreate
from app.services.indiamart import IndiaMartLeadBatchResult, IndiaMartLeadListResult
from app.services.lead_scoring import LeadQualificationEngine

LEAD_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def make_indiamart_lead(**overrides: object) -> SimpleNamespace:
    values = {
        "id": LEAD_ID,
        "lead_fingerprint": "a" * 64,
        "external_lead_id": "IM-123",
        "product_name": "Hydraulic Pump",
        "product_category": "Industrial Pumps",
        "quantity": "10 Pieces",
        "order_value": "Rs 50,000",
        "purpose": "Business Use",
        "lead_time": "Immediate",
        "buyer_name": "Rahul Sharma",
        "business_name": "Sharma Industries",
        "phone_available": True,
        "email_available": False,
        "whatsapp_available": True,
        "business_available": True,
        "address_available": True,
        "years_active": 7,
        "requirements_count": 14,
        "replies_count": 3,
        "city": "Pune",
        "state": "Maharashtra",
        "source_url": "https://seller.indiamart.com/bltxn/",
        "raw_payload": {},
        "lead_score_value": 32,
        "lead_score_category": "COLD",
        "lead_score_reasons": [
            "Lead has phone contact information.",
            "Lead source indicates buying intent.",
            "Buyer is in a supported target geography.",
        ],
        "lead_score_explanation": {
            "score": 32,
            "category": "COLD",
            "explanation": "Lead score is 32 (COLD).",
        },
        "lead_scored_at": datetime(2026, 6, 5, tzinfo=UTC),
        "extracted_at": datetime(2026, 6, 5, tzinfo=UTC),
        "created_at": datetime(2026, 6, 5, tzinfo=UTC),
        "updated_at": datetime(2026, 6, 5, tzinfo=UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeIndiaMartLeadService:
    def __init__(self) -> None:
        self.upsert_payload = None
        self.batch_payload = None
        self.list_filters = None
        self.delete_all_called = False

    async def upsert_lead(self, payload):
        self.upsert_payload = payload
        return make_indiamart_lead(
            lead_fingerprint=payload.lead_fingerprint,
            product_name=payload.product_name,
        ), True

    async def upsert_batch(self, payload):
        self.batch_payload = payload
        return IndiaMartLeadBatchResult(
            items=[make_indiamart_lead(product_name=item.product_name) for item in payload.items],
            created=len(payload.items),
            updated=0,
        )

    async def list_leads(self, filters):
        self.list_filters = filters
        return IndiaMartLeadListResult(
            items=[make_indiamart_lead()],
            total=1,
            page=filters.page,
            size=filters.size,
        )

    async def delete_all_leads(self):
        self.delete_all_called = True
        return 7


@pytest.fixture
def fake_service() -> FakeIndiaMartLeadService:
    return FakeIndiaMartLeadService()


@pytest.fixture
def client(fake_service: FakeIndiaMartLeadService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_indiamart_lead_service] = lambda: fake_service
    return TestClient(app)


def test_upsert_indiamart_lead_generates_fingerprint(
    client: TestClient,
    fake_service: FakeIndiaMartLeadService,
) -> None:
    response = client.post(
        "/indiamart/leads",
        json={
            "product_name": "Hydraulic Pump",
            "buyer_name": "Rahul Sharma",
            "business_name": "Sharma Industries",
            "city": "Pune",
            "state": "Maharashtra",
            "phone_available": True,
            "requirements_count": 14,
        },
    )

    assert response.status_code == 201
    assert len(response.json()["lead_fingerprint"]) == 64
    assert fake_service.upsert_payload.product_name == "Hydraulic Pump"
    assert fake_service.upsert_payload.lead_fingerprint is not None


def test_upsert_indiamart_leads_batch(
    client: TestClient,
    fake_service: FakeIndiaMartLeadService,
) -> None:
    response = client.post(
        "/indiamart/leads/batch",
        json={
            "items": [
                {
                    "external_lead_id": "IM-123",
                    "product_name": "Hydraulic Pump",
                    "city": "Pune",
                    "state": "Maharashtra",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["created"] == 1
    assert response.json()["updated"] == 0
    assert fake_service.batch_payload.items[0].external_lead_id == "IM-123"


def test_upsert_indiamart_lead_response_includes_score(client: TestClient) -> None:
    response = client.post(
        "/indiamart/leads",
        json={
            "product_name": "Hydraulic Pump",
            "buyer_name": "Rahul Sharma",
            "business_name": "Sharma Industries",
            "city": "Pune",
            "state": "Maharashtra",
            "phone_available": True,
            "requirements_count": 14,
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["lead_score_value"] == 32
    assert body["lead_score_category"] == "COLD"
    assert body["lead_score_explanation"]["category"] == "COLD"


def test_list_indiamart_leads_supports_filters(
    client: TestClient,
    fake_service: FakeIndiaMartLeadService,
) -> None:
    response = client.get(
        "/indiamart/leads",
        params={
            "page": 1,
            "size": 10,
            "city": "Pune",
            "state": "Maharashtra",
            "sort_by": "buyer_name",
            "sort_order": "asc",
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert fake_service.list_filters.city == "Pune"
    assert fake_service.list_filters.sort_by == "buyer_name"


def test_delete_all_indiamart_leads(
    client: TestClient,
    fake_service: FakeIndiaMartLeadService,
) -> None:
    response = client.delete("/indiamart/leads")

    assert response.status_code == 200
    assert response.json() == {"deleted": 7}
    assert fake_service.delete_all_called is True


@pytest.mark.asyncio
async def test_indiamart_service_scores_lead_before_upsert() -> None:
    from app.services.indiamart import IndiaMartLeadService

    class FakeRepository:
        def __init__(self) -> None:
            self.lead = None

        async def upsert(self, lead):
            self.lead = lead
            return lead, True

    repository = FakeRepository()
    service = IndiaMartLeadService(
        repository,
        LeadQualificationEngine.from_yaml("configs/lead_scoring.yml"),
    )

    lead, was_created = await service.upsert_lead(
        payload=IndiaMartLeadCreate(
            product_name="Hydraulic Pump",
            product_category="Manufacturing",
            buyer_name="Rahul Sharma",
            business_name="Sharma Industries",
            city="Pune",
            state="Maharashtra",
            phone_available=True,
        )
    )

    assert was_created is True
    assert repository.lead is lead
    assert lead.lead_score_value == 45
    assert lead.lead_score_category == "WARM"
    assert "Lead source indicates buying intent." in lead.lead_score_reasons
    assert lead.lead_score_explanation["recommended_next_action"] == (
        "Enrich missing contact details, then send a targeted follow-up."
    )
    assert lead.lead_scored_at is not None
