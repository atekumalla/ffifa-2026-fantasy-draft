"""OpenAI ChatGPT fallback for fetching match scores when the API is unavailable.

Uses the latest openai Python SDK (v1.x+) with structured output parsing.
This is a fallback — results should be verified as LLMs can occasionally hallucinate.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

from src.config import Config
from src.models.match import Match, MatchStage, MatchStatus

logger = logging.getLogger(__name__)

# System prompt that instructs GPT on how to respond
_SYSTEM_PROMPT = """You are a sports data assistant. When asked about FIFA World Cup 2026 match results,
respond ONLY with a JSON array of match objects. Each object must have exactly these fields:

{
  "home_team": "Country Name",
  "away_team": "Country Name",
  "home_goals": <int or null if not played>,
  "away_goals": <int or null if not played>,
  "home_penalties": <int or null>,
  "away_penalties": <int or null>,
  "status": "finished" | "scheduled" | "in_play",
  "stage": "group" | "round_of_32" | "round_of_16" | "quarter_final" | "semi_final" | "third_place" | "final"
}

IMPORTANT:
- Only include goals scored in regular time and extra time (NOT penalty shootout goals) in home_goals/away_goals
- Penalty shootout results go in home_penalties/away_penalties
- If you are unsure about a result, set status to "scheduled" and goals to null
- Respond with ONLY the JSON array, no other text
"""


class LLMFallback:
    """ChatGPT-based fallback for match score retrieval."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = OpenAI(api_key=api_key or Config.OPENAI_API_KEY)
        self.model = model or Config.OPENAI_MODEL

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(3))
    def fetch_match_results(
        self, match_date: date, known_matches: list[Match] | None = None
    ) -> list[Match]:
        """
        Ask ChatGPT for World Cup match results on a given date.

        Args:
            match_date: The date to query results for.
            known_matches: Optional list of known scheduled matches to give context.

        Returns:
            List of Match objects with scores filled in.
        """
        # Build the user prompt
        user_prompt = f"What are the FIFA World Cup 2026 match results for {match_date.strftime('%B %d, %Y')}?"

        if known_matches:
            games_list = "\n".join(
                f"- {m.home_team} vs {m.away_team} ({m.stage.value})"
                for m in known_matches
            )
            user_prompt += f"\n\nHere are the scheduled matches for that day:\n{games_list}"

        logger.info(f"Querying ChatGPT for match results on {match_date}")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Low temperature for factual accuracy
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        return self._parse_response(content, match_date)

    def fetch_specific_match(
        self, home_team: str, away_team: str, match_date: date
    ) -> Optional[Match]:
        """Query ChatGPT for a specific match result."""
        user_prompt = (
            f"What was the final score of {home_team} vs {away_team} "
            f"in the FIFA World Cup 2026 on {match_date.strftime('%B %d, %Y')}? "
            f"Include whether it went to penalties."
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=500,
        )

        content = response.choices[0].message.content.strip()
        matches = self._parse_response(content, match_date)
        return matches[0] if matches else None

    def _parse_response(self, content: str, match_date: date) -> list[Match]:
        """Parse the JSON response from ChatGPT into Match objects."""
        try:
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0]

            data = json.loads(content)
            if not isinstance(data, list):
                data = [data]

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {content}")
            return []

        matches = []
        for item in data:
            try:
                status_str = item.get("status", "scheduled")
                status_map = {
                    "finished": MatchStatus.FINISHED,
                    "in_play": MatchStatus.IN_PLAY,
                    "scheduled": MatchStatus.SCHEDULED,
                }

                stage_str = item.get("stage", "group")
                stage_map = {
                    "group": MatchStage.GROUP,
                    "round_of_32": MatchStage.ROUND_OF_32,
                    "round_of_16": MatchStage.ROUND_OF_16,
                    "quarter_final": MatchStage.QUARTER_FINAL,
                    "semi_final": MatchStage.SEMI_FINAL,
                    "third_place": MatchStage.THIRD_PLACE,
                    "final": MatchStage.FINAL,
                }

                match = Match(
                    match_id=f"llm_{match_date}_{item['home_team']}_{item['away_team']}",
                    match_date=match_date,
                    stage=stage_map.get(stage_str, MatchStage.GROUP),
                    home_team=item["home_team"],
                    away_team=item["away_team"],
                    home_goals=item.get("home_goals"),
                    away_goals=item.get("away_goals"),
                    home_penalties=item.get("home_penalties"),
                    away_penalties=item.get("away_penalties"),
                    status=status_map.get(status_str, MatchStatus.SCHEDULED),
                )
                matches.append(match)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse match from LLM response: {e}")
                continue

        logger.info(f"LLM returned {len(matches)} match(es) for {match_date}")
        return matches
