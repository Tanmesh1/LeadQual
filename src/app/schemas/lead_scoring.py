from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

LeadScoreCategory: TypeAlias = Literal["HOT", "WARM", "COLD"]


class LeadScoringRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_information: dict[str, Any] = Field(default_factory=dict)
    buyer_information: dict[str, Any] = Field(default_factory=dict)


class LeadScoringResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    category: LeadScoreCategory
    reasons: list[str]


class LeadExplanationRequest(LeadScoringRequest):
    score: int = Field(ge=0, le=100)


class LeadScoreFactor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    section: str
    section_label: str
    field: str
    observed_value: Any | None = None
    impact: Literal["positive", "negative"]
    points: int = Field(ge=0)
    explanation: str


class LeadExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    category: LeadScoreCategory
    explanation: str
    why_score_is_high: list[str]
    why_score_is_low: list[str]
    biggest_positive_factors: list[LeadScoreFactor]
    biggest_negative_factors: list[LeadScoreFactor]
    recommended_next_action: str


class LeadScoreRuleDistribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    field: str
    observed_value: Any | None = None
    matched: bool
    raw_points_possible: float = Field(ge=0)
    raw_points_earned: float = Field(ge=0)
    raw_points_lost: float = Field(ge=0)
    normalized_points_possible: float = Field(ge=0)
    normalized_points_earned: float = Field(ge=0)
    normalized_points_lost: float = Field(ge=0)
    explanation: str


class LeadScoreSectionDistribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str
    section_label: str
    section_weight: float = Field(ge=0)
    raw_points_possible: float = Field(ge=0)
    raw_points_earned: float = Field(ge=0)
    raw_points_lost: float = Field(ge=0)
    normalized_points_possible: float = Field(ge=0)
    normalized_points_earned: float = Field(ge=0)
    normalized_points_lost: float = Field(ge=0)
    rules: list[LeadScoreRuleDistribution]


class LeadScoreDistributionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    category: LeadScoreCategory
    normalized_points_possible: float = Field(ge=0)
    normalized_points_earned: float = Field(ge=0)
    normalized_points_lost: float = Field(ge=0)
    sections: list[LeadScoreSectionDistribution]
    reasons: list[str]
