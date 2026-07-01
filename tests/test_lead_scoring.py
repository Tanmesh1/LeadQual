from pathlib import Path

from fastapi.testclient import TestClient

from app.api.v1.lead_scoring import get_lead_qualification_engine
from app.main import create_app
from app.services.lead_scoring import LeadQualificationEngine

CONFIG_PATH = Path("configs/lead_scoring.yml")


def test_engine_scores_hot_lead_with_explanations() -> None:
    engine = LeadQualificationEngine.from_yaml(CONFIG_PATH)

    result = engine.score(
        lead_information={
            "job_title": "VP Sales",
            "email": "jane@example.com",
            "phone": "+1-555-0100",
            "source": "demo_request",
        },
        buyer_information={
            "industry": "Software",
            "employee_count": 250,
            "annual_revenue_usd": 2_500_000,
            "country": "US",
        },
    )

    assert result.score == 100
    assert result.category == "HOT"
    assert "Decision-maker title matched." in result.reasons
    assert "Buyer company size fits the ideal customer profile." in result.reasons


def test_engine_normalizes_partial_score_to_cold() -> None:
    engine = LeadQualificationEngine.from_yaml(CONFIG_PATH)

    result = engine.score(
        lead_information={
            "job_title": "Marketing Associate",
            "email": "sam@example.com",
            "source": "webinar",
        },
        buyer_information={
            "industry": "Manufacturing",
            "employee_count": 200,
            "country": "India",
        },
    )

    assert result.score == 42
    assert result.category == "COLD"
    assert result.reasons == [
        "Lead has a usable email address.",
        "Buyer industry is in the target market.",
        "Buyer company size fits the ideal customer profile.",
        "Buyer is in a supported target geography.",
    ]


def test_engine_scores_empty_input_as_cold() -> None:
    engine = LeadQualificationEngine.from_yaml(CONFIG_PATH)

    result = engine.score(lead_information={}, buyer_information={})

    assert result.score == 0
    assert result.category == "COLD"
    assert result.reasons == ["No configured qualification rules matched this lead."]


def test_engine_explains_lead_score_with_ranked_factors() -> None:
    engine = LeadQualificationEngine.from_yaml(CONFIG_PATH)

    result = engine.explain(
        score=42,
        lead_information={
            "job_title": "Marketing Associate",
            "email": "sam@example.com",
            "source": "webinar",
        },
        buyer_information={
            "industry": "Manufacturing",
            "employee_count": 200,
            "country": "India",
        },
    )

    assert result.score == 42
    assert result.category == "COLD"
    assert result.biggest_positive_factors[0].name == "target_industry"
    assert result.biggest_positive_factors[0].points == 15
    assert result.biggest_negative_factors[0].name == "decision_maker_title"
    assert result.biggest_negative_factors[0].points == 25
    assert result.why_score_is_high == [
        "Buyer industry is in the target market.",
        "Buyer company size fits the ideal customer profile.",
        "Lead has a usable email address.",
    ]
    assert result.why_score_is_low[0] == (
        "Decision maker title was not satisfied by job_title='Marketing Associate'."
    )
    assert result.recommended_next_action == (
        "Route this lead to nurture and revisit when stronger fit or intent signals appear."
    )


def test_engine_returns_exact_score_distribution() -> None:
    engine = LeadQualificationEngine.from_yaml(CONFIG_PATH)

    result = engine.distribution(
        lead_information={
            "job_title": "Marketing Associate",
            "email": "sam@example.com",
            "source": "webinar",
        },
        buyer_information={
            "industry": "Manufacturing",
            "employee_count": 200,
            "country": "India",
        },
    )

    assert result.score == 42
    assert result.category == "COLD"
    assert result.normalized_points_possible == 100
    assert result.normalized_points_earned == 42
    assert result.normalized_points_lost == 58

    lead_section = result.sections[0]
    assert lead_section.section == "lead_information"
    assert lead_section.raw_points_possible == 60
    assert lead_section.raw_points_earned == 10
    assert lead_section.normalized_points_earned == 10
    assert lead_section.normalized_points_lost == 50
    assert lead_section.rules[0].name == "decision_maker_title"
    assert lead_section.rules[0].matched is False
    assert lead_section.rules[0].raw_points_lost == 25
    assert lead_section.rules[0].normalized_points_lost == 25
    assert lead_section.rules[1].name == "valid_contact_email"
    assert lead_section.rules[1].matched is True
    assert lead_section.rules[1].normalized_points_earned == 10

    buyer_section = result.sections[1]
    assert buyer_section.section == "buyer_information"
    assert buyer_section.raw_points_possible == 40
    assert buyer_section.raw_points_earned == 32
    assert buyer_section.normalized_points_earned == 32
    assert buyer_section.normalized_points_lost == 8
    assert buyer_section.rules[2].name == "revenue_fit"
    assert buyer_section.rules[2].matched is False
    assert buyer_section.rules[2].raw_points_lost == 8


def test_score_lead_api() -> None:
    app = create_app()
    get_lead_qualification_engine.cache_clear()
    client = TestClient(app)

    response = client.post(
        "/lead-scoring/score",
        json={
            "lead_information": {
                "job_title": "Founder",
                "email": "founder@example.com",
                "source": "pricing_request",
            },
            "buyer_information": {
                "industry": "Logistics",
                "employee_count": 75,
                "annual_revenue_usd": 1_200_000,
                "country": "United States",
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "score": 92,
        "category": "HOT",
        "reasons": [
            "Decision-maker title matched.",
            "Lead has a usable email address.",
            "Lead source indicates buying intent.",
            "Buyer industry is in the target market.",
            "Buyer company size fits the ideal customer profile.",
            "Buyer revenue suggests ability to purchase.",
            "Buyer is in a supported target geography.",
        ],
    }


def test_score_lead_distribution_api() -> None:
    app = create_app()
    get_lead_qualification_engine.cache_clear()
    client = TestClient(app)

    response = client.post(
        "/lead-scoring/distribution",
        json={
            "lead_information": {
                "job_title": "Founder",
                "email": "founder@example.com",
                "source": "pricing_request",
            },
            "buyer_information": {
                "industry": "Logistics",
                "employee_count": 75,
                "annual_revenue_usd": 1_200_000,
                "country": "United States",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 92
    assert body["category"] == "HOT"
    assert body["normalized_points_earned"] == 92
    assert body["normalized_points_lost"] == 8
    assert body["sections"][0]["normalized_points_earned"] == 52
    assert body["sections"][0]["rules"][2]["name"] == "phone_available"
    assert body["sections"][0]["rules"][2]["normalized_points_lost"] == 8


def test_explain_lead_score_api() -> None:
    app = create_app()
    get_lead_qualification_engine.cache_clear()
    client = TestClient(app)

    response = client.post(
        "/lead-scoring/explain",
        json={
            "score": 92,
            "lead_information": {
                "job_title": "Founder",
                "email": "founder@example.com",
                "source": "pricing_request",
            },
            "buyer_information": {
                "industry": "Logistics",
                "employee_count": 75,
                "annual_revenue_usd": 1_200_000,
                "country": "United States",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 92
    assert body["category"] == "HOT"
    assert body["recommended_next_action"] == (
        "Contact this lead immediately and prioritize a direct sales follow-up."
    )
    assert body["biggest_positive_factors"][0] == {
        "name": "decision_maker_title",
        "section": "lead_information",
        "section_label": "Lead Information",
        "field": "job_title",
        "observed_value": "Founder",
        "impact": "positive",
        "points": 25,
        "explanation": "Decision-maker title matched.",
    }
    assert body["biggest_negative_factors"][0]["name"] == "phone_available"
