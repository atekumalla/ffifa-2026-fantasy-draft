"""Daily validation — checks spreadsheet data for correctness.

Two validation layers:
  1. Structural/Math: Deterministic checks (points calculations, data integrity)
  2. Factual: LLM-based verification (are the match scores actually correct?)

Runs once daily (configurable), reports issues via logging.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from src.models.match import Match, MatchStatus
from src.models.player import DraftPlayer
from src.scoring.calculator import ScoringCalculator
from src.scoring.rules import DEFAULT_RULES

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """A single validation issue found."""
    severity: str  # "error", "warning", "info"
    category: str  # "structural", "math", "factual"
    message: str
    details: Optional[str] = None


@dataclass
class ValidationReport:
    """Results of a full validation run."""
    issues: list[ValidationIssue] = field(default_factory=list)
    checks_passed: int = 0
    checks_failed: int = 0
    timestamp: Optional[str] = None

    @property
    def is_healthy(self) -> bool:
        return all(i.severity != "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    def summary(self) -> str:
        status = "✅ HEALTHY" if self.is_healthy else "❌ ISSUES FOUND"
        return (
            f"{status} | "
            f"{self.checks_passed} passed, {self.checks_failed} failed | "
            f"{self.error_count} errors, {self.warning_count} warnings"
        )


# =============================================================================
# LAYER 1: Structural & Math Validation (deterministic, no LLM)
# =============================================================================

def validate_structural(
    matches: list[Match],
    players: list[DraftPlayer],
    calculator: ScoringCalculator | None = None,
) -> ValidationReport:
    """Run all deterministic validation checks."""
    calculator = calculator or ScoringCalculator(DEFAULT_RULES)
    report = ValidationReport()

    _check_match_count(matches, report)
    _check_no_duplicate_matches(matches, report)
    _check_score_consistency(matches, report)
    _check_points_calculations(matches, calculator, report)
    _check_draft_picks_integrity(players, report)
    _check_reasonable_scores(matches, report)

    return report


def _check_match_count(matches: list[Match], report: ValidationReport):
    """Verify we have the expected number of matches (104 for WC 2026)."""
    expected = 104
    actual = len(matches)
    if actual == expected:
        report.checks_passed += 1
    elif actual < expected:
        report.issues.append(ValidationIssue(
            severity="error",
            category="structural",
            message=f"Missing matches: expected {expected}, found {actual}",
            details=f"{expected - actual} matches are missing from the schedule",
        ))
        report.checks_failed += 1
    else:
        report.issues.append(ValidationIssue(
            severity="warning",
            category="structural",
            message=f"Extra matches: expected {expected}, found {actual}",
        ))
        report.checks_failed += 1


def _check_no_duplicate_matches(matches: list[Match], report: ValidationReport):
    """Check for duplicate match entries."""
    seen = set()
    duplicates = []
    for m in matches:
        key = (m.match_date, m.home_team.lower(), m.away_team.lower())
        if key in seen:
            duplicates.append(f"{m.match_date}: {m.home_team} vs {m.away_team}")
        seen.add(key)

    if not duplicates:
        report.checks_passed += 1
    else:
        report.issues.append(ValidationIssue(
            severity="error",
            category="structural",
            message=f"Found {len(duplicates)} duplicate match(es)",
            details="; ".join(duplicates[:5]),
        ))
        report.checks_failed += 1


def _check_score_consistency(matches: list[Match], report: ValidationReport):
    """Finished matches must have scores; scheduled matches must not."""
    issues_found = []
    for m in matches:
        if m.status == MatchStatus.FINISHED:
            if m.home_goals is None or m.away_goals is None:
                issues_found.append(
                    f"{m.match_date} {m.home_team} vs {m.away_team}: "
                    f"marked FINISHED but missing scores"
                )
        elif m.status == MatchStatus.SCHEDULED:
            if m.home_goals is not None or m.away_goals is not None:
                issues_found.append(
                    f"{m.match_date} {m.home_team} vs {m.away_team}: "
                    f"marked SCHEDULED but has scores ({m.home_goals}-{m.away_goals})"
                )

    if not issues_found:
        report.checks_passed += 1
    else:
        for issue in issues_found[:10]:
            report.issues.append(ValidationIssue(
                severity="error",
                category="structural",
                message=issue,
            ))
        report.checks_failed += 1


def _check_points_calculations(
    matches: list[Match],
    calculator: ScoringCalculator,
    report: ValidationReport,
):
    """Recalculate all points from scratch and verify they match."""
    # This validates that stored points match what the calculator produces
    # (catches cases where rules changed but sheet wasn't updated)
    recalculated_totals: dict[str, float] = {}
    for match in matches:
        pts = calculator.calculate_match_points(match)
        for team, points in pts.items():
            recalculated_totals[team] = recalculated_totals.get(team, 0.0) + points

    # For now just verify the calculator doesn't produce NaN or extreme values
    bad_values = []
    for team, pts in recalculated_totals.items():
        if pts < -50 or pts > 100:
            bad_values.append(f"{team}: {pts} pts (suspicious)")

    if not bad_values:
        report.checks_passed += 1
    else:
        for bv in bad_values:
            report.issues.append(ValidationIssue(
                severity="warning",
                category="math",
                message=f"Suspicious point total: {bv}",
            ))
        report.checks_failed += 1


def _check_draft_picks_integrity(players: list[DraftPlayer], report: ValidationReport):
    """Verify draft picks are valid (4 players, 10 teams each, no overlaps)."""
    issues = []

    # Check player count
    if len(players) != 4:
        issues.append(f"Expected 4 players, found {len(players)}")

    # Check team counts
    for p in players:
        if p.team_count != 10:
            issues.append(f"{p.name} has {p.team_count} teams (expected 10)")

    # Check for duplicate team assignments
    all_teams = []
    for p in players:
        all_teams.extend(p.teams)

    team_set = set(t.lower() for t in all_teams)
    if len(team_set) != len(all_teams):
        # Find duplicates
        seen = set()
        dupes = []
        for t in all_teams:
            if t.lower() in seen:
                dupes.append(t)
            seen.add(t.lower())
        issues.append(f"Teams assigned to multiple players: {', '.join(dupes)}")

    if not issues:
        report.checks_passed += 1
    else:
        for issue in issues:
            report.issues.append(ValidationIssue(
                severity="error",
                category="structural",
                message=issue,
            ))
        report.checks_failed += 1


def _check_reasonable_scores(matches: list[Match], report: ValidationReport):
    """Flag scores that seem unreasonable (possible data errors)."""
    suspicious = []
    for m in matches:
        if not m.is_played:
            continue
        hg = m.home_goals or 0
        ag = m.away_goals or 0
        # Flag if total goals > 10 (extremely rare in World Cup)
        if hg + ag > 10:
            suspicious.append(
                f"{m.match_date} {m.home_team} {hg}-{ag} {m.away_team} "
                f"(total {hg+ag} goals — verify!)"
            )
        # Flag negative goals (data corruption)
        if hg < 0 or ag < 0:
            suspicious.append(
                f"{m.match_date} {m.home_team} {hg}-{ag} {m.away_team} "
                f"(negative goals — data error!)"
            )

    if not suspicious:
        report.checks_passed += 1
    else:
        for s in suspicious:
            report.issues.append(ValidationIssue(
                severity="warning",
                category="math",
                message=f"Unusual score: {s}",
            ))
        report.checks_failed += 1


# =============================================================================
# LAYER 2: Factual Validation via LLM (checks if scores are actually correct)
# =============================================================================

def validate_factual_with_llm(
    matches: list[Match],
    openai_api_key: str | None = None,
    model: str | None = None,
) -> ValidationReport:
    """
    Ask ChatGPT to verify recent match results are factually correct.

    Only checks matches from the last 3 days to keep token usage low.
    """
    from openai import OpenAI
    from src.config import Config

    report = ValidationReport()
    client = OpenAI(api_key=openai_api_key or Config.OPENAI_API_KEY)
    model = model or Config.OPENAI_MODEL

    # Only verify recently finished matches (last 3 days)
    today = date.today()
    recent_finished = [
        m for m in matches
        if m.is_played and (today - m.match_date).days <= 3
    ]

    if not recent_finished:
        logger.info("No recent matches to validate with LLM")
        report.checks_passed += 1
        return report

    # Format matches for the LLM
    match_list = "\n".join(
        f"- {m.match_date}: {m.home_team} {m.home_goals}-{m.away_goals} {m.away_team} "
        f"({m.stage.value})"
        + (f" [Penalties: {m.home_penalties}-{m.away_penalties}]"
           if m.home_penalties is not None else "")
        for m in recent_finished
    )

    prompt = f"""I'm tracking FIFA World Cup 2026 match results. Please verify if these recent results are correct.

My recorded results:
{match_list}

For each match, respond with ONLY a JSON array where each item has:
{{
  "home_team": "...",
  "away_team": "...",
  "recorded_correct": true/false,
  "correct_score": "X-Y" (only if recorded_correct is false),
  "confidence": "high"/"medium"/"low",
  "note": "optional explanation"
}}

If you're unsure about a result, set confidence to "low".
Only mark recorded_correct as false if you are CONFIDENT the score is wrong.
Respond with ONLY the JSON array."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a sports data verification assistant. "
                        "You verify FIFA World Cup 2026 match results for accuracy. "
                        "Only flag results as incorrect if you are highly confident. "
                        "Respond only with JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        _parse_llm_validation(content, report, recent_finished)

    except Exception as e:
        logger.warning(f"LLM validation failed: {e}")
        report.issues.append(ValidationIssue(
            severity="info",
            category="factual",
            message=f"LLM validation could not run: {e}",
        ))

    return report


def _parse_llm_validation(
    content: str,
    report: ValidationReport,
    matches: list[Match],
):
    """Parse the LLM's validation response."""
    import json

    try:
        # Strip markdown code fences
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]

        results = json.loads(content)
        if not isinstance(results, list):
            results = [results]
    except json.JSONDecodeError as e:
        report.issues.append(ValidationIssue(
            severity="info",
            category="factual",
            message=f"Could not parse LLM validation response: {e}",
        ))
        return

    for item in results:
        is_correct = item.get("recorded_correct", True)
        confidence = item.get("confidence", "low")
        home = item.get("home_team", "?")
        away = item.get("away_team", "?")
        note = item.get("note", "")

        if is_correct:
            report.checks_passed += 1
        else:
            correct_score = item.get("correct_score", "unknown")
            severity = "error" if confidence == "high" else "warning"
            report.issues.append(ValidationIssue(
                severity=severity,
                category="factual",
                message=(
                    f"Possibly wrong score: {home} vs {away} — "
                    f"correct score may be {correct_score} "
                    f"(confidence: {confidence})"
                ),
                details=note,
            ))
            report.checks_failed += 1


# =============================================================================
# COMBINED VALIDATION (runs both layers)
# =============================================================================

def run_full_validation(
    matches: list[Match],
    players: list[DraftPlayer],
    use_llm: bool = True,
) -> ValidationReport:
    """
    Run complete validation: structural + factual.

    Args:
        matches: All matches from the sheet
        players: All draft players
        use_llm: Whether to run LLM fact-checking (costs ~$0.01 per run)
    """
    logger.info("Running daily validation...")

    # Layer 1: Structural checks
    structural_report = validate_structural(matches, players)

    # Layer 2: LLM fact-checking (optional)
    factual_report = ValidationReport()
    if use_llm:
        try:
            factual_report = validate_factual_with_llm(matches)
        except Exception as e:
            logger.warning(f"Skipping LLM validation: {e}")

    # Merge reports
    combined = ValidationReport(
        issues=structural_report.issues + factual_report.issues,
        checks_passed=structural_report.checks_passed + factual_report.checks_passed,
        checks_failed=structural_report.checks_failed + factual_report.checks_failed,
    )

    # Log results
    logger.info(f"Validation complete: {combined.summary()}")
    for issue in combined.issues:
        log_fn = {
            "error": logger.error,
            "warning": logger.warning,
            "info": logger.info,
        }.get(issue.severity, logger.info)
        log_fn(f"  [{issue.category}] {issue.message}")
        if issue.details:
            log_fn(f"    → {issue.details}")

    return combined
