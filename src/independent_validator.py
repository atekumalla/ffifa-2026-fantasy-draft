"""Independent validator for the /api/validate endpoint.

Fetches from football-data.org as ground truth and compares against the app's
in-memory match state. Returns a summary dict + a full text report for download.

This is intentionally separate from src/validation.py (which only does internal
sheet consistency checks). This module acts as an external judge.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from src.config import Config
from src.data_sources.football_api import FootballDataAPI
from src.models.match import Match, MatchStatus
from src.models.player import DraftPlayer
from src.scoring.calculator import ScoringCalculator
from src.scoring.rules import DEFAULT_RULES

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

TOTAL_WC_MATCHES = 104  # Includes TBD placeholder slots

STAGE_ORDER = [
    "group", "round_of_32", "round_of_16",
    "quarter_final", "semi_final", "third_place", "final",
]
STAGE_LABEL = {
    "group":         "Group Stage",
    "round_of_32":   "Round of 32",
    "round_of_16":   "Round of 16",
    "quarter_final": "Quarter Final",
    "semi_final":    "Semi Final",
    "third_place":   "3rd Place",
    "final":         "Final",
}
EXPECTED_COUNTS = {
    "group": 72, "round_of_32": 16, "round_of_16": 8,
    "quarter_final": 4, "semi_final": 2, "third_place": 1, "final": 1,
}

# Canonical draft picks — loaded from the draft config file
# (config/draft_config.json by default; override via DRAFT_CONFIG_FILE).
from src.draft_config import get_team_aliases, load_draft_config


def _draft_picks() -> dict[str, list[str]]:
    """Player → list of picked teams, from the draft config."""
    return {p.name: list(p.teams) for p in load_draft_config().players}


# Aliases that server.py normalises before storing
_ALIASES = get_team_aliases()

DRAFT_PICKS: dict[str, list[str]] = _draft_picks()

TEAM_TO_PLAYER: dict[str, str] = {t: p for p, ts in DRAFT_PICKS.items() for t in ts}


# ── Small helpers ──────────────────────────────────────────────────────────────

def _sv(m: Match) -> str:
    """Stage enum → string value."""
    return m.stage.value


def _canonical(name: str) -> str:
    return _ALIASES.get(name, name)


def _score_str(m: Match) -> str:
    if m.home_goals is None:
        return "— vs —"
    s = f"{m.home_goals}–{m.away_goals}"
    if m.home_penalties is not None and m.away_penalties is not None:
        s += f" (pens {m.home_penalties}–{m.away_penalties})"
    return s


def _match_key(m: Match) -> frozenset:
    return frozenset([m.home_team, m.away_team])


# ── Analysis helpers ───────────────────────────────────────────────────────────

def _compute_team_pts(matches: list[Match], calc: ScoringCalculator) -> dict[str, float]:
    totals: dict[str, float] = {}
    for m in matches:
        for team, pts in calc.calculate_match_points(m).items():
            totals[team] = round(totals.get(team, 0.0) + pts, 2)
    return totals


def _compute_player_totals(team_pts: dict[str, float]) -> dict[str, float]:
    return {
        player: round(sum(team_pts.get(_canonical(t), 0.0) for t in teams), 2)
        for player, teams in DRAFT_PICKS.items()
    }


def _compute_player_breakdown(matches: list[Match], calc: ScoringCalculator) -> dict[str, dict]:
    result = {
        p: {
            "total": 0.0,
            "by_stage": defaultdict(float),
            "by_team": {t: 0.0 for t in teams},
            "match_log": [],
        }
        for p, teams in DRAFT_PICKS.items()
    }
    for m in sorted(
        (m for m in matches if m.status == MatchStatus.FINISHED),
        key=lambda m: (m.match_date, m.kickoff_time or datetime.min),
    ):
        pts_map = calc.calculate_match_points(m)
        for player, teams in DRAFT_PICKS.items():
            for team in teams:
                if team not in (m.home_team, m.away_team):
                    continue
                tp = pts_map.get(team, 0.0)
                d = result[player]
                d["by_team"][team] = round(d["by_team"][team] + tp, 2)
                d["by_stage"][_sv(m)] = round(d["by_stage"][_sv(m)] + tp, 2)
                d["total"] = round(d["total"] + tp, 2)
                res = m.result_for_team.get(team, "")
                opp = m.away_team if team == m.home_team else m.home_team
                d["match_log"].append({
                    "date":     m.match_date,
                    "stage":    _sv(m),
                    "group":    m.group,
                    "team":     team,
                    "opponent": opp,
                    "score":    _score_str(m),
                    "result":   res,
                    "pts":      tp,
                })
    return result


def _group_standings(matches: list[Match], calc: ScoringCalculator) -> dict[str, dict[str, dict]]:
    standings: dict[str, dict[str, dict]] = {}

    def _init():
        return {"played": 0, "won": 0, "drawn": 0, "lost": 0,
                "gf": 0, "ga": 0, "gd": 0, "pts": 0, "fantasy_pts": 0.0}

    for m in matches:
        if _sv(m) != "group" or m.status != MatchStatus.FINISHED or not m.group:
            continue
        g = m.group
        standings.setdefault(g, {})
        standings[g].setdefault(m.home_team, _init())
        standings[g].setdefault(m.away_team, _init())
        hg, ag = m.home_goals or 0, m.away_goals or 0
        pts_map = calc.calculate_match_points(m)
        for team, goals_f, goals_a in [(m.home_team, hg, ag), (m.away_team, ag, hg)]:
            res = m.result_for_team.get(team, "")
            s = standings[g][team]
            s["played"] += 1
            s["gf"] += goals_f
            s["ga"] += goals_a
            s["gd"] = s["gf"] - s["ga"]
            if res == "win":
                s["won"] += 1; s["pts"] += 3
            elif res == "draw":
                s["drawn"] += 1; s["pts"] += 1
            else:
                s["lost"] += 1
            s["fantasy_pts"] = round(s["fantasy_pts"] + pts_map.get(team, 0.0), 2)
    return standings


def _get_eliminated(matches: list[Match]) -> dict[str, str]:
    eliminated: dict[str, str] = {}
    for m in sorted(
        (m for m in matches if m.stage.is_knockout and m.status == MatchStatus.FINISHED),
        key=lambda m: STAGE_ORDER.index(_sv(m)),
    ):
        for team, res in m.result_for_team.items():
            if res == "loss":
                eliminated[team] = _sv(m)
    return eliminated


# ── Report builder ─────────────────────────────────────────────────────────────

def _build_report(
    now:             datetime,
    api_matches:     list[Match],
    api_breakdown:   dict,
    by_stage:        dict[str, list[Match]],
    stage_breakdown: dict,
    eliminated:      dict[str, str],
    r32_teams:       set[str],
    group_elims:     set[str],
    still_in:        set[str],
    lb_comparison:   list[dict],
    issues:          list[dict],
    tbd_count:       int,
    standings:       dict,
    calc:            ScoringCalculator,
) -> str:
    lines: list[str] = []

    def h1(t):   lines.append(f"# {t}\n")
    def h2(t):   lines.append(f"\n## {t}\n")
    def h3(t):   lines.append(f"\n### {t}\n")
    def p(*a):   lines.append(" ".join(str(x) for x in a))
    def blank(): lines.append("")
    def hr():    lines.append("\n---\n")

    errors = [i for i in issues if i["level"] == "ERROR"]
    warns  = [i for i in issues if i["level"] == "WARN"]
    oks    = [i for i in issues if i["level"] == "OK"]
    health = "✅ HEALTHY" if not errors else f"❌ {len(errors)} ISSUE(S) FOUND"
    finished = [m for m in api_matches if m.status == MatchStatus.FINISHED]

    # Header
    h1("⚽ FIFA 2026 Fantasy Draft — Scoring Validation Report")
    p(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}")
    p(f"**Data source:** football-data.org API v4  (Competition: WC)")
    p(f"**Comparison:** App in-memory state vs independent API calculation")
    blank()

    # Executive summary
    h2("📊 Executive Summary")
    p("| Metric | Value |")
    p("|--------|-------|")
    p(f"| **Overall Status** | {health} |")
    p(f"| Total matches in API | **{TOTAL_WC_MATCHES}** |")
    p(f"| Finished | {len(finished)} |")
    p(f"| Scheduled (teams known) | {sum(1 for m in api_matches if m.status == MatchStatus.SCHEDULED)} |")
    p(f"| Teams TBD (future knockouts) | {tbd_count} |")
    for stage in STAGE_ORDER:
        s = stage_breakdown.get(stage, {})
        total = s.get("with_teams", 0) + s.get("tbd", 0)
        p(f"| {STAGE_LABEL[stage]} | {s.get('finished', 0)} finished / {total} total |")
    p(f"| Checks passed | {len(oks)} ✅ |")
    p(f"| Warnings | {len(warns)} ⚠️ |")
    p(f"| Errors | {len(errors)} ❌ |")
    hr()

    # Leaderboard
    h2("🏆 Fantasy Draft Leaderboard")
    h3("Independent Calculation (API Ground Truth)")
    rank_emojis = ["🥇", "🥈", "🥉", "4️⃣"]
    p("| Rank | Player | **Total** | Group | R32 | R16 | QF | SF | Final/3rd |")
    p("|------|--------|-----------|-------|-----|-----|----|----|-----------|")
    sorted_players = sorted(api_breakdown.items(), key=lambda x: -x[1]["total"])
    for i, (player, data) in enumerate(sorted_players):
        rank = rank_emojis[i] if i < len(rank_emojis) else str(i + 1)
        p(f"| {rank} | **{player}** | **{data['total']}** "
          f"| {round(data['by_stage'].get('group', 0.0), 2)} "
          f"| {round(data['by_stage'].get('round_of_32', 0.0), 2)} "
          f"| {round(data['by_stage'].get('round_of_16', 0.0), 2)} "
          f"| {round(data['by_stage'].get('quarter_final', 0.0), 2)} "
          f"| {round(data['by_stage'].get('semi_final', 0.0), 2)} "
          f"| {round(data['by_stage'].get('final', 0.0) + data['by_stage'].get('third_place', 0.0), 2)} |")
    blank()
    h3("App vs Our Calculation")
    p("| Player | Our Calc | App Calc | Diff | Status |")
    p("|--------|----------|----------|------|--------|")
    for row in lb_comparison:
        diff_str = f"{row['diff']:+.2f}" if row["diff"] is not None else "N/A"
        status = "✅" if row["match"] else "❌ MISMATCH"
        p(f"| **{row['name']}** | {row['our_calc']} | {row['app_calc']} | {diff_str} | {status} |")
    hr()

    # Points progression per player
    h2("📈 Points Progression Per Player")
    for player, data in sorted_players:
        h3(f"{player}  —  {data['total']} pts")
        p("**Team breakdown:**")
        blank()
        p("| Team | Pts | Owner | Status |")
        p("|------|-----|-------|--------|")
        for team, pts in sorted(data["by_team"].items(), key=lambda x: -x[1]):
            owner = TEAM_TO_PLAYER.get(team, "—")
            if team in eliminated:
                status = f"❌ Out ({STAGE_LABEL.get(eliminated[team], eliminated[team])})"
            elif team in r32_teams:
                status = "🟢 In knockouts"
            elif team in group_elims:
                status = "❌ Out (Group Stage)"
            else:
                status = "⏳ TBD"
            p(f"| {team} | **{pts}** | {owner} | {status} |")
        blank()
        p("**Match-by-match (chronological):**")
        blank()
        p("| Date | Stage | Team | Opponent | Score | Result | Pts | Running Total |")
        p("|------|-------|------|----------|-------|--------|-----|---------------|")
        running = 0.0
        for entry in data["match_log"]:
            running = round(running + entry["pts"], 2)
            slbl = f"Group {entry['group']}" if entry["group"] else STAGE_LABEL.get(entry["stage"], entry["stage"])
            rlbl = {"win": "✅ Win", "draw": "🤝 Draw", "loss": "❌ Loss"}.get(entry["result"], entry["result"])
            p(f"| {entry['date']} | {slbl} | {entry['team']} | {entry['opponent']} "
              f"| {entry['score']} | {rlbl} | +{entry['pts']} | {running} |")
        p(f"\n> **Total: {data['total']} pts**")
        blank()
    hr()

    # Group standings
    h2("🔵 Group Stage Analysis")
    for group in sorted(standings.keys()):
        grp = standings[group]
        h3(f"Group {group}")
        sorted_teams = sorted(grp.items(), key=lambda x: (-x[1]["pts"], -x[1]["gd"], -x[1]["gf"]))
        p("| Pos | Team | P | W | D | L | GF | GA | GD | Pts | Fantasy Pts | Owner | Advanced? |")
        p("|-----|------|---|---|---|---|----|----|-----|-----|-------------|-------|-----------|")
        for pos, (team, s) in enumerate(sorted_teams, 1):
            icon = ["🥇", "🥈", "3️⃣", "4️⃣"][pos - 1] if pos <= 4 else str(pos)
            owner = TEAM_TO_PLAYER.get(team, "—")
            adv = "✅ Yes" if team in r32_teams else "❌ No"
            p(f"| {icon} | **{team}** | {s['played']} | {s['won']} | {s['drawn']} | {s['lost']} "
              f"| {s['gf']} | {s['ga']} | {s['gd']:+d} | {s['pts']} | {s['fantasy_pts']} | {owner} | {adv} |")
        grp_matches = sorted(
            [m for m in api_matches if _sv(m) == "group" and m.group == group
             and m.status == MatchStatus.FINISHED],
            key=lambda m: m.match_date,
        )
        if grp_matches:
            blank()
            p("**Results:**")
            blank()
            p("| Date | Home | Score | Away | H.Pts | A.Pts |")
            p("|------|------|-------|------|-------|-------|")
            for m in grp_matches:
                pts = calc.calculate_match_points(m)
                p(f"| {m.match_date} | {m.home_team} | **{_score_str(m)}** | {m.away_team} "
                  f"| {pts.get(m.home_team, 0)} | {pts.get(m.away_team, 0)} |")
        blank()
    hr()

    # Knockout analysis
    h2("⚡ Knockout Stage Analysis")
    for stage in STAGE_ORDER[1:]:
        stage_matches = sorted(by_stage.get(stage, []), key=lambda m: m.match_date)
        if not stage_matches:
            continue
        fin_in   = [m for m in stage_matches if m.status == MatchStatus.FINISHED]
        sched_in = [m for m in stage_matches if m.status == MatchStatus.SCHEDULED]
        h3(f"{STAGE_LABEL[stage]}  ({len(fin_in)}/{len(stage_matches)} played)")
        if fin_in:
            p("| Date | Home (Owner) | Score | Away (Owner) | Winner | H.Pts | A.Pts |")
            p("|------|-------------|-------|-------------|--------|-------|-------|")
            for m in fin_in:
                pts = calc.calculate_match_points(m)
                h_res = m.result_for_team.get(m.home_team, "")
                winner = m.home_team if h_res == "win" else m.away_team
                h_own = TEAM_TO_PLAYER.get(m.home_team, "—")
                a_own = TEAM_TO_PLAYER.get(m.away_team, "—")
                p(f"| {m.match_date} | {m.home_team} *({h_own})* | **{_score_str(m)}** "
                  f"| {m.away_team} *({a_own})* | 🏆 **{winner}** "
                  f"| {pts.get(m.home_team, 0)} | {pts.get(m.away_team, 0)} |")
        if sched_in:
            blank()
            p("**Upcoming:**")
            blank()
            p("| Date | Home | Away |")
            p("|------|------|------|")
            for m in sched_in:
                p(f"| {m.match_date} | {m.home_team} | {m.away_team} |")
        blank()
    hr()

    # Team progression
    h2("🗺️ Team Progression Tracker")
    h3("Still in Tournament")
    if still_in:
        p(f"**{len(still_in)} teams remain:**")
        blank()
        p("| Team | Owner | Furthest Stage |")
        p("|------|-------|----------------|")
        for team in sorted(still_in):
            owner = TEAM_TO_PLAYER.get(team, "—")
            played_stages = [_sv(m) for m in api_matches if m.stage.is_knockout and (m.home_team == team or m.away_team == team)]
            latest = max(played_stages, key=lambda s: STAGE_ORDER.index(s), default="round_of_32")
            p(f"| **{team}** | {owner} | {STAGE_LABEL[latest]} |")
    blank()
    h3("Eliminated — By Stage")
    if group_elims:
        p(f"**❌ Group Stage ({len(group_elims)} teams):**")
        blank()
        p("| Team | Owner |")
        p("|------|-------|")
        for team in sorted(group_elims):
            p(f"| {team} | {TEAM_TO_PLAYER.get(team, '—')} |")
        blank()
    for stage in STAGE_ORDER[1:]:
        out = sorted(t for t, s in eliminated.items() if s == stage)
        if out:
            p(f"**❌ {STAGE_LABEL[stage]} ({len(out)} teams):**")
            blank()
            p("| Team | Owner |")
            p("|------|-------|")
            for team in out:
                p(f"| {team} | {TEAM_TO_PLAYER.get(team, '—')} |")
            blank()
    hr()

    # All finished matches
    h2("📋 All Finished Matches — Complete Scoring Breakdown")
    all_fin = sorted(finished, key=lambda m: (STAGE_ORDER.index(_sv(m)), m.match_date))
    p(f"Total: **{len(all_fin)}** finished matches")
    cur_stage = None
    for m in all_fin:
        if _sv(m) != cur_stage:
            cur_stage = _sv(m)
            blank()
            p(f"### {STAGE_LABEL[cur_stage]}")
            blank()
            p("| Date | Home | Score | Away | H.Pts | A.Pts | H.Owner | A.Owner |")
            p("|------|------|-------|------|-------|-------|---------|---------|")
        pts = calc.calculate_match_points(m)
        h_own = TEAM_TO_PLAYER.get(m.home_team, "—")
        a_own = TEAM_TO_PLAYER.get(m.away_team, "—")
        p(f"| {m.match_date} | {m.home_team} | **{_score_str(m)}** | {m.away_team} "
          f"| {pts.get(m.home_team, 0)} | {pts.get(m.away_team, 0)} | {h_own} | {a_own} |")
    hr()

    # Validation checks
    h2("🔍 Validation Checks")
    for issue in issues:
        icon = {"OK": "✅", "WARN": "⚠️", "ERROR": "❌"}[issue["level"]]
        detail = f": _{issue.get('detail', '')}_" if issue.get("detail") else ""
        p(f"- {icon} {issue['msg']}{detail}")
    hr()

    # Upcoming
    upcoming = sorted([m for m in api_matches if m.status == MatchStatus.SCHEDULED], key=lambda m: m.match_date)
    if upcoming:
        h2("📅 Remaining Scheduled Matches")
        p("| Date | Stage | Home | Away | H.Owner | A.Owner |")
        p("|------|-------|------|------|---------|---------|")
        for m in upcoming:
            p(f"| {m.match_date} | {STAGE_LABEL.get(_sv(m), _sv(m))} | {m.home_team} | {m.away_team} "
              f"| {TEAM_TO_PLAYER.get(m.home_team, '—')} | {TEAM_TO_PLAYER.get(m.away_team, '—')} |")
        hr()

    # Scoring rules
    h2("📚 Scoring Rules")
    r = DEFAULT_RULES
    p("| Scenario | Points |")
    p("|----------|--------|")
    p(f"| Group Win | **{r.group_win}** |")
    p(f"| Group Draw (each) | **{r.group_draw}** |")
    p(f"| Group Goal Scored | **{r.group_goal_scored}** per goal |")
    p(f"| Knockout Win | **{r.knockout_win}** |")
    p(f"| Knockout Goal (reg + ET only) | **{r.knockout_goal_scored}** per goal |")
    p("| Penalty shootout goals | **0** |")
    p("| Goals conceded / Losses | **0** |")
    blank()
    p(f"_Report generated {now.strftime('%Y-%m-%d %H:%M UTC')}_")

    return "\n".join(lines)


# ── Public entry point ─────────────────────────────────────────────────────────

def run_independent_validation(
    app_matches:  list[Match],
    app_players:  list[DraftPlayer],
    api_key:      Optional[str] = None,
) -> tuple[dict, str]:
    """
    Fetch from football-data.org, compute independently, compare with app state.

    Args:
        app_matches:  Matches currently in the app's memory (from Google Sheet).
        app_players:  Draft players currently in the app's memory.
        api_key:      football-data.org API key (defaults to Config.FOOTBALL_API_KEY).

    Returns:
        (summary_dict, full_report_text)
    """
    now = datetime.now(timezone.utc)
    calc = ScoringCalculator(DEFAULT_RULES)

    # Fetch from API (1 HTTP call)
    logger.info("Independent validator: fetching from football-data.org …")
    api = FootballDataAPI(api_key=api_key or Config.FOOTBALL_API_KEY)
    api_matches = api.fetch_all_matches()   # skips TBD, normalises team names
    tbd_count = TOTAL_WC_MATCHES - len(api_matches)

    finished_api  = [m for m in api_matches if m.status == MatchStatus.FINISHED]
    scheduled_api = [m for m in api_matches if m.status == MatchStatus.SCHEDULED]
    logger.info(f"  → {len(api_matches)} parsed  ({len(finished_api)} finished, "
                f"{len(scheduled_api)} scheduled, {tbd_count} TBD)")

    # Compute from API data (ground truth)
    api_team_pts   = _compute_team_pts(api_matches, calc)
    api_player_pts = _compute_player_totals(api_team_pts)
    api_breakdown  = _compute_player_breakdown(api_matches, calc)
    eliminated     = _get_eliminated(api_matches)
    standings      = _group_standings(api_matches, calc)

    r32_teams: set[str] = {
        t for m in api_matches if _sv(m) == "round_of_32"
        for t in (m.home_team, m.away_team)
    }
    group_teams: set[str] = {
        t for m in api_matches if _sv(m) == "group"
        for t in (m.home_team, m.away_team)
    }
    group_elims = group_teams - r32_teams
    still_in    = r32_teams - set(eliminated.keys())

    # Compute from app's in-memory data (same scoring calc, different source)
    app_team_pts   = _compute_team_pts(app_matches, calc)
    app_player_pts = _compute_player_totals(app_team_pts)

    # ── Validation checks ──────────────────────────────────────────────────────
    issues: list[dict] = []
    def _ok(msg, detail=""):   issues.append({"level": "OK",    "msg": msg, "detail": detail})
    def _warn(msg, detail=""):  issues.append({"level": "WARN",  "msg": msg, "detail": detail})
    def _err(msg, detail=""):   issues.append({"level": "ERROR", "msg": msg, "detail": detail})

    # 1. Finished match count
    app_fin_count = sum(1 for m in app_matches if m.status == MatchStatus.FINISHED)
    if app_fin_count == len(finished_api):
        _ok(f"Finished match count: {len(finished_api)}")
    else:
        _warn("Finished match count mismatch",
              f"API: {len(finished_api)}, App: {app_fin_count}")

    # 2. Score comparison — API vs app, for every finished match
    app_idx = {_match_key(m): m for m in app_matches if m.status == MatchStatus.FINISHED}
    score_ok = True
    for api_m in finished_api:
        key = _match_key(api_m)
        app_m = app_idx.get(key)
        if app_m is None:
            _warn("Match missing in app",
                  f"{api_m.home_team} vs {api_m.away_team} ({api_m.match_date})")
            continue
        # Orient app match to match API home/away order
        if app_m.home_team == api_m.home_team:
            ahg, aag = app_m.home_goals, app_m.away_goals
        else:
            ahg, aag = app_m.away_goals, app_m.home_goals
        if api_m.home_goals != ahg or api_m.away_goals != aag:
            _err("Score mismatch",
                 f"{api_m.home_team} vs {api_m.away_team} ({api_m.match_date}): "
                 f"API={api_m.home_goals}-{api_m.away_goals}, App={ahg}-{aag}")
            score_ok = False
    if score_ok:
        _ok(f"All {len(finished_api)} match scores verified correct")

    # 3. Player points comparison
    lb_comparison: list[dict] = []
    for player in sorted(api_player_pts, key=lambda p: -api_player_pts[p]):
        our   = api_player_pts[player]
        app_v = app_player_pts.get(player)
        diff  = round(our - app_v, 2) if app_v is not None else None
        ok    = diff is not None and abs(diff) < 0.02
        lb_comparison.append({
            "name": player, "our_calc": our,
            "app_calc": app_v, "diff": diff, "match": ok,
        })
        if ok:
            _ok(f"{player} points match: {our} pts")
        else:
            _err(f"Points mismatch: {player}",
                 f"Our: {our}, App: {app_v}, Diff: {diff:+.2f}" if diff is not None else "N/A")

    # 4. Score plausibility
    bad = [
        f"{m.home_team} vs {m.away_team}: {m.home_goals}-{m.away_goals}"
        for m in finished_api
        if m.home_goals is not None and (
            m.home_goals < 0 or m.away_goals < 0 or (m.home_goals + m.away_goals) > 15
        )
    ]
    if bad:
        for b in bad:
            _warn("Implausible score", b)
    else:
        _ok("All scores are plausible")

    # Stage breakdown
    by_stage: dict[str, list[Match]] = defaultdict(list)
    for m in api_matches:
        by_stage[_sv(m)].append(m)

    stage_breakdown = {
        stage: {
            "with_teams": len(by_stage[stage]),
            "finished":   sum(1 for m in by_stage[stage] if m.status == MatchStatus.FINISHED),
            "scheduled":  sum(1 for m in by_stage[stage] if m.status == MatchStatus.SCHEDULED),
            "tbd":        EXPECTED_COUNTS.get(stage, 0) - len(by_stage[stage]),
        }
        for stage in STAGE_ORDER
    }

    errors = [i for i in issues if i["level"] == "ERROR"]
    warns  = [i for i in issues if i["level"] == "WARN"]
    oks    = [i for i in issues if i["level"] == "OK"]

    summary = {
        "healthy":            len(errors) == 0,
        "generated_at":       now.isoformat(),
        "checks_passed":      len(oks),
        "checks_warned":      len(warns),
        "checks_failed":      len(errors),
        "total_api_matches":  TOTAL_WC_MATCHES,
        "matches_with_teams": len(api_matches),
        "matches_finished":   len(finished_api),
        "matches_scheduled":  len(scheduled_api),
        "matches_tbd":        tbd_count,
        "leaderboard":        lb_comparison,
        "stage_breakdown":    stage_breakdown,
        "teams_remaining":    len(still_in),
        "teams_out_group":    len(group_elims),
        "teams_out_knockout": len(eliminated),
        "issues":             [i for i in issues if i["level"] != "OK"],
    }

    report_text = _build_report(
        now, api_matches, api_breakdown, by_stage, stage_breakdown,
        eliminated, r32_teams, group_elims, still_in,
        lb_comparison, issues, tbd_count, standings, calc,
    )

    return summary, report_text
