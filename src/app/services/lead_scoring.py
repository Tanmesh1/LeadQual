from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from app.schemas.lead_scoring import (
    LeadExplanationResponse,
    LeadScoreDistributionResponse,
    LeadScoreFactor,
    LeadScoreRuleDistribution,
    LeadScoreSectionDistribution,
    LeadScoringResponse,
)


class LeadScoringConfigError(ValueError):
    """Raised when the YAML scoring configuration is invalid."""


@dataclass(frozen=True)
class RuleResult:
    matched: bool
    points: Decimal
    reason: str | None


@dataclass(frozen=True)
class FactorResult:
    name: str
    section: str
    section_label: str
    field: str
    observed_value: Any
    matched: bool
    contribution: Decimal
    reason: str | None


class LeadQualificationEngine:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self.config = config
        self._validate_config()

    @classmethod
    def from_yaml(cls, path: str | Path) -> LeadQualificationEngine:
        config_path = Path(path)
        with config_path.open(encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}
        if not isinstance(config, Mapping):
            raise LeadScoringConfigError("Scoring config must be a YAML mapping")
        return cls(config)

    def score(
        self,
        *,
        lead_information: Mapping[str, Any],
        buyer_information: Mapping[str, Any],
    ) -> LeadScoringResponse:
        sections = self.config["sections"]
        section_inputs = {
            "lead_information": lead_information,
            "buyer_information": buyer_information,
        }

        weighted_score = Decimal("0")
        max_weight = Decimal("0")
        reasons: list[str] = []

        for section_name, section_config in sections.items():
            section_weight = _decimal(section_config["weight"], f"{section_name}.weight")
            rules = section_config.get("rules", [])
            available_points = sum(
                _decimal(rule["points"], f"{section_name}.{rule['name']}.points")
                for rule in rules
            )

            if available_points <= 0:
                continue

            earned_points = Decimal("0")
            section_data = section_inputs.get(section_name, {})
            for rule in rules:
                result = self._evaluate_rule(rule, section_data)
                if result.matched:
                    earned_points += result.points
                    if result.reason:
                        reasons.append(result.reason)

            weighted_score += (earned_points / available_points) * section_weight
            max_weight += section_weight

        score = int((weighted_score / max_weight * 100).quantize(Decimal("1"))) if max_weight else 0
        score = max(0, min(100, score))

        if not reasons:
            reasons.append("No configured qualification rules matched this lead.")

        return LeadScoringResponse(
            score=score,
            category=self._classify(score),
            reasons=reasons,
        )

    def explain(
        self,
        *,
        score: int,
        lead_information: Mapping[str, Any],
        buyer_information: Mapping[str, Any],
    ) -> LeadExplanationResponse:
        factors = self._collect_factors(
            lead_information=lead_information,
            buyer_information=buyer_information,
        )
        category = self._classify(score)
        positive_factors = sorted(
            (factor for factor in factors if factor.matched),
            key=lambda factor: factor.contribution,
            reverse=True,
        )
        negative_factors = sorted(
            (factor for factor in factors if not factor.matched),
            key=lambda factor: factor.contribution,
            reverse=True,
        )

        biggest_positive_factors = [
            self._to_factor_schema(factor, impact="positive") for factor in positive_factors[:3]
        ]
        biggest_negative_factors = [
            self._to_factor_schema(factor, impact="negative") for factor in negative_factors[:3]
        ]

        why_score_is_high = [
            factor.explanation for factor in biggest_positive_factors
        ] or ["No configured positive qualification factors matched this lead."]
        why_score_is_low = [
            factor.explanation for factor in biggest_negative_factors
        ] or ["No major negative qualification gaps were found in the configured rules."]

        return LeadExplanationResponse(
            score=score,
            category=category,
            explanation=self._build_summary(
                score=score,
                category=category,
                positive_factors=biggest_positive_factors,
                negative_factors=biggest_negative_factors,
            ),
            why_score_is_high=why_score_is_high,
            why_score_is_low=why_score_is_low,
            biggest_positive_factors=biggest_positive_factors,
            biggest_negative_factors=biggest_negative_factors,
            recommended_next_action=self._recommend_next_action(
                category=category,
                negative_factors=biggest_negative_factors,
            ),
        )

    def distribution(
        self,
        *,
        lead_information: Mapping[str, Any],
        buyer_information: Mapping[str, Any],
    ) -> LeadScoreDistributionResponse:
        sections = self.config["sections"]
        section_inputs = {
            "lead_information": lead_information,
            "buyer_information": buyer_information,
        }
        max_weight = self._scorable_weight_total()

        section_distributions: list[LeadScoreSectionDistribution] = []
        total_earned = Decimal("0")
        reasons: list[str] = []

        for section_name, section_config in sections.items():
            rules = section_config.get("rules", [])
            raw_possible = sum(
                _decimal(rule["points"], f"{section_name}.{rule['name']}.points")
                for rule in rules
            )
            if raw_possible <= 0 or max_weight <= 0:
                continue

            section_weight = _decimal(section_config["weight"], f"{section_name}.weight")
            normalized_possible = section_weight / max_weight * 100
            section_data = section_inputs.get(section_name, {})
            section_label = str(section_config.get("label") or _humanize(section_name))

            raw_earned = Decimal("0")
            rule_distributions: list[LeadScoreRuleDistribution] = []
            for rule in rules:
                result = self._evaluate_rule(rule, section_data)
                raw_rule_possible = _decimal(
                    rule["points"],
                    f"{section_name}.{rule['name']}.points",
                )
                raw_rule_earned = result.points
                raw_rule_lost = raw_rule_possible - raw_rule_earned
                normalized_rule_possible = raw_rule_possible / raw_possible * normalized_possible
                normalized_rule_earned = raw_rule_earned / raw_possible * normalized_possible
                normalized_rule_lost = raw_rule_lost / raw_possible * normalized_possible

                raw_earned += raw_rule_earned
                if result.reason:
                    reasons.append(result.reason)

                rule_distributions.append(
                    LeadScoreRuleDistribution(
                        name=str(rule["name"]),
                        field=str(rule["field"]),
                        observed_value=_get_value(section_data, str(rule["field"])),
                        matched=result.matched,
                        raw_points_possible=_round(raw_rule_possible),
                        raw_points_earned=_round(raw_rule_earned),
                        raw_points_lost=_round(raw_rule_lost),
                        normalized_points_possible=_round(normalized_rule_possible),
                        normalized_points_earned=_round(normalized_rule_earned),
                        normalized_points_lost=_round(normalized_rule_lost),
                        explanation=result.reason
                        or self._negative_factor_reason(
                            FactorResult(
                                name=str(rule["name"]),
                                section=str(section_name),
                                section_label=section_label,
                                field=str(rule["field"]),
                                observed_value=_get_value(section_data, str(rule["field"])),
                                matched=False,
                                contribution=normalized_rule_lost,
                                reason=None,
                            )
                        ),
                    )
                )

            normalized_earned = raw_earned / raw_possible * normalized_possible
            total_earned += normalized_earned
            section_distributions.append(
                LeadScoreSectionDistribution(
                    section=str(section_name),
                    section_label=section_label,
                    section_weight=_round(section_weight),
                    raw_points_possible=_round(raw_possible),
                    raw_points_earned=_round(raw_earned),
                    raw_points_lost=_round(raw_possible - raw_earned),
                    normalized_points_possible=_round(normalized_possible),
                    normalized_points_earned=_round(normalized_earned),
                    normalized_points_lost=_round(normalized_possible - normalized_earned),
                    rules=rule_distributions,
                )
            )

        score = int(total_earned.quantize(Decimal("1")))
        score = max(0, min(100, score))
        normalized_possible_total = Decimal("100") if max_weight > 0 else Decimal("0")

        if not reasons:
            reasons.append("No configured qualification rules matched this lead.")

        return LeadScoreDistributionResponse(
            score=score,
            category=self._classify(score),
            normalized_points_possible=_round(normalized_possible_total),
            normalized_points_earned=_round(total_earned),
            normalized_points_lost=_round(normalized_possible_total - total_earned),
            sections=section_distributions,
            reasons=reasons,
        )

    def _validate_config(self) -> None:
        classification = self.config.get("classification")
        sections = self.config.get("sections")

        if not isinstance(classification, Mapping):
            raise LeadScoringConfigError("Scoring config requires classification thresholds")
        if not isinstance(sections, Mapping) or not sections:
            raise LeadScoringConfigError("Scoring config requires at least one section")

        for threshold_name in ("hot_min", "warm_min"):
            _decimal(classification.get(threshold_name), f"classification.{threshold_name}")

        for section_name, section_config in sections.items():
            if not isinstance(section_config, Mapping):
                raise LeadScoringConfigError(f"{section_name} must be a mapping")
            _decimal(section_config.get("weight"), f"{section_name}.weight")
            rules = section_config.get("rules")
            if not isinstance(rules, list):
                raise LeadScoringConfigError(f"{section_name}.rules must be a list")
            for rule in rules:
                self._validate_rule(section_name, rule)

    def _validate_rule(self, section_name: str, rule: Any) -> None:
        if not isinstance(rule, Mapping):
            raise LeadScoringConfigError(f"{section_name}.rules entries must be mappings")
        for key in ("name", "field", "type", "points"):
            if key not in rule:
                raise LeadScoringConfigError(f"{section_name} rule is missing {key}")
        _decimal(rule["points"], f"{section_name}.{rule['name']}.points")

    def _evaluate_rule(self, rule: Mapping[str, Any], data: Mapping[str, Any]) -> RuleResult:
        value = _get_value(data, str(rule["field"]))
        rule_type = str(rule["type"])
        matched = False

        if rule_type == "exists":
            matched = value not in (None, "")
        elif rule_type == "equals_any":
            matched = _normalize(value) in {_normalize(item) for item in rule.get("values", [])}
        elif rule_type == "contains":
            matched = _normalize(rule.get("value")) in _normalize(value)
        elif rule_type == "contains_any":
            normalized_value = _normalize(value)
            matched = any(_normalize(item) in normalized_value for item in rule.get("values", []))
        elif rule_type == "range":
            number = _maybe_decimal(value)
            minimum = _maybe_decimal(rule.get("min"))
            maximum = _maybe_decimal(rule.get("max"))
            matched = (
                number is not None
                and minimum is not None
                and maximum is not None
                and minimum <= number <= maximum
            )
        elif rule_type == "min":
            number = _maybe_decimal(value)
            minimum = _maybe_decimal(rule.get("min"))
            matched = number is not None and minimum is not None and number >= minimum
        elif rule_type == "boolean_true":
            matched = value is True
        else:
            raise LeadScoringConfigError(f"Unsupported rule type: {rule_type}")

        points = _decimal(rule["points"], str(rule["name"]))
        return RuleResult(
            matched=matched,
            points=points if matched else Decimal("0"),
            reason=str(rule.get("reason")) if matched and rule.get("reason") else None,
        )

    def _collect_factors(
        self,
        *,
        lead_information: Mapping[str, Any],
        buyer_information: Mapping[str, Any],
    ) -> list[FactorResult]:
        sections = self.config["sections"]
        section_inputs = {
            "lead_information": lead_information,
            "buyer_information": buyer_information,
        }
        max_weight = self._scorable_weight_total()
        if max_weight <= 0:
            return []

        factors: list[FactorResult] = []
        for section_name, section_config in sections.items():
            rules = section_config.get("rules", [])
            available_points = sum(
                _decimal(rule["points"], f"{section_name}.{rule['name']}.points")
                for rule in rules
            )
            if available_points <= 0:
                continue

            section_weight = _decimal(section_config["weight"], f"{section_name}.weight")
            section_data = section_inputs.get(section_name, {})
            section_label = str(section_config.get("label") or _humanize(section_name))

            for rule in rules:
                result = self._evaluate_rule(rule, section_data)
                rule_points = _decimal(rule["points"], f"{section_name}.{rule['name']}.points")
                contribution = (rule_points / available_points) * section_weight / max_weight * 100
                factors.append(
                    FactorResult(
                        name=str(rule["name"]),
                        section=str(section_name),
                        section_label=section_label,
                        field=str(rule["field"]),
                        observed_value=_get_value(section_data, str(rule["field"])),
                        matched=result.matched,
                        contribution=contribution,
                        reason=result.reason
                        or self._fallback_factor_reason(rule, matched=result.matched),
                    )
                )
        return factors

    def _scorable_weight_total(self) -> Decimal:
        total = Decimal("0")
        for section_name, section_config in self.config["sections"].items():
            rules = section_config.get("rules", [])
            available_points = sum(
                _decimal(rule["points"], f"{section_name}.{rule['name']}.points")
                for rule in rules
            )
            if available_points > 0:
                total += _decimal(section_config["weight"], f"{section_name}.weight")
        return total

    def _to_factor_schema(self, factor: FactorResult, *, impact: str) -> LeadScoreFactor:
        explanation = factor.reason or _humanize(factor.name)
        if impact == "negative":
            explanation = self._negative_factor_reason(factor)

        return LeadScoreFactor(
            name=factor.name,
            section=factor.section,
            section_label=factor.section_label,
            field=factor.field,
            observed_value=factor.observed_value,
            impact=impact,
            points=int(factor.contribution.quantize(Decimal("1"))),
            explanation=explanation,
        )

    def _fallback_factor_reason(self, rule: Mapping[str, Any], *, matched: bool) -> str:
        rule_label = _humanize(str(rule["name"]))
        if matched:
            return f"{rule_label} matched."
        return f"{rule_label} did not match."

    def _negative_factor_reason(self, factor: FactorResult) -> str:
        observed_value = _format_observed_value(factor.observed_value)
        rule_label = _humanize(factor.name)
        if observed_value:
            return f"{rule_label} was not satisfied by {factor.field}={observed_value}."
        return f"{rule_label} was not satisfied because {factor.field} is missing."

    def _build_summary(
        self,
        *,
        score: int,
        category: str,
        positive_factors: list[LeadScoreFactor],
        negative_factors: list[LeadScoreFactor],
    ) -> str:
        if positive_factors and negative_factors:
            return (
                f"Lead score is {score} ({category}) because {positive_factors[0].explanation} "
                f"The biggest remaining gap is: {negative_factors[0].explanation}"
            )
        if positive_factors:
            return (
                f"Lead score is {score} ({category}) because the strongest configured signals "
                f"matched, led by: {positive_factors[0].explanation}"
            )
        return (
            f"Lead score is {score} ({category}) because no configured qualification signals "
            "matched strongly enough."
        )

    def _recommend_next_action(
        self,
        *,
        category: str,
        negative_factors: list[LeadScoreFactor],
    ) -> str:
        missing_contact = any(factor.field in {"email", "phone"} for factor in negative_factors)
        if category == "HOT":
            return "Contact this lead immediately and prioritize a direct sales follow-up."
        if category == "WARM":
            if missing_contact:
                return "Enrich missing contact details, then send a targeted follow-up."
            return "Send a targeted follow-up and confirm buying timeline, budget, and authority."
        if missing_contact:
            return "Enrich contact data before routing this lead to a nurture sequence."
        return "Route this lead to nurture and revisit when stronger fit or intent signals appear."

    def _classify(self, score: int) -> str:
        classification = self.config["classification"]
        hot_min = int(_decimal(classification["hot_min"], "classification.hot_min"))
        warm_min = int(_decimal(classification["warm_min"], "classification.warm_min"))

        if score >= hot_min:
            return "HOT"
        if score >= warm_min:
            return "WARM"
        return "COLD"


def _get_value(data: Mapping[str, Any], field_path: str) -> Any:
    value: Any = data
    for part in field_path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _format_observed_value(value: Any) -> str:
    if value in (None, ""):
        return ""
    return repr(value)


def _round(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _decimal(value: Any, field_name: str) -> Decimal:
    number = _maybe_decimal(value)
    if number is None:
        raise LeadScoringConfigError(f"{field_name} must be numeric")
    return number


def _maybe_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
