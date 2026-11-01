"""PandaScore schedule/result adapter. Source observations are not settlements."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Literal

import httpx
from pydantic import ValidationError

from app.fixture_data import FixtureImportDocument, FixtureRecord, ResultRecord


Game = Literal["valorant", "cs2", "r6siege"]
GAME_PATH = {"valorant": "valorant", "cs2": "csgo", "r6siege": "r6siege"}
PROVIDER_ID = "pandascore"
API_BASE = "https://api.pandascore.co"


class PandaScoreError(RuntimeError):
    """A provider response could not be used safely."""


class PandaScoreRateLimited(PandaScoreError):
    """The provider request budget is exhausted; retry in a later poll."""


def _digest(value: dict[str, object]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "0x" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _team(opponent: object) -> tuple[str, str] | None:
    if not isinstance(opponent, dict):
        return None
    if opponent.get("type") not in (None, "Team"):
        return None
    team = opponent.get("opponent")
    if not isinstance(team, dict):
        return None
    identifier, name = team.get("id"), team.get("name")
    if not isinstance(identifier, int) or identifier < 0 or not isinstance(name, str) or not name.strip():
        return None
    return str(identifier), name.strip()


def normalize_match(raw: object, game: Game) -> tuple[FixtureRecord, ResultRecord | None] | None:
    """Discard ambiguous listings instead of guessing teams, time, or winner."""
    if not isinstance(raw, dict):
        return None
    match_id = raw.get("id")
    opponents = raw.get("opponents")
    if not isinstance(match_id, int) or match_id < 0 or not isinstance(opponents, list) or len(opponents) != 2:
        return None
    first, second = _team(opponents[0]), _team(opponents[1])
    if first is None or second is None or first[0] == second[0]:
        return None
    scheduled_at, modified_at = raw.get("scheduled_at"), raw.get("modified_at")
    if not isinstance(scheduled_at, str) or not isinstance(modified_at, str):
        return None
    try:
        start = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        updated = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if start.tzinfo is None or updated.tzinfo is None:
        return None

    status = raw.get("status")
    statuses = {"not_started": "scheduled", "running": "live", "postponed": "postponed",
                "finished": "completed", "canceled": "canceled"}
    if status not in statuses:
        return None
    source_url = f"{API_BASE}/matches/{match_id}"
    evidence_hash = _digest(raw)
    identity = {"provider_id": PROVIDER_ID, "game_id": game, "external_match_id": str(match_id)}
    try:
        fixture = FixtureRecord.model_validate({
            **identity, "scheduled_start": start, "match_status": statuses[status],
            "team_a_id": first[0], "team_a_name": first[1],
            "team_b_id": second[0], "team_b_name": second[1],
            "source_updated_at": updated, "evidence_url": source_url, "evidence_hash": evidence_hash,
        })
    except ValidationError:
        return None

    result = None
    if status == "finished":
        winner = raw.get("winner_id")
        if raw.get("draw") is True and winner is None:
            result_status, winner_id = "tied", None
        elif isinstance(winner, int) and str(winner) in {first[0], second[0]} and raw.get("draw") is not True:
            result_status, winner_id = "completed", str(winner)
        else:
            return fixture, None
        result = ResultRecord.model_validate({
            **identity, "match_status": result_status, "winner_team_id": winner_id,
            "source_updated_at": updated, "evidence_url": source_url, "evidence_hash": evidence_hash,
        })
    elif status == "canceled" and raw.get("forfeit") is False and raw.get("winner_id") is None:
        result = ResultRecord.model_validate({
            **identity, "match_status": "canceled", "winner_team_id": None,
            "source_updated_at": updated, "evidence_url": source_url, "evidence_hash": evidence_hash,
        })
    return fixture, result


class PandaScoreClient:
    """Bounded REST poller; never sends the token in a URL or exposes raw responses."""

    def __init__(self, token: str, *, client: httpx.Client | None = None,
                 base_url: str = API_BASE, page_size: int = 50, max_pages: int = 4) -> None:
        if not token.strip():
            raise ValueError("PandaScore token is required")
        if not 1 <= page_size <= 100 or not 1 <= max_pages <= 100:
            raise ValueError("invalid PandaScore pagination bounds")
        self.token = token
        self.client = client or httpx.Client(timeout=10)
        self.owns_client = client is None
        self.base_url = base_url.rstrip("/")
        self.page_size = page_size
        self.max_pages = max_pages

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    def __enter__(self) -> PandaScoreClient:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def fetch(self, game: Game, *, include_past: bool = True) -> FixtureImportDocument:
        if game not in GAME_PATH:
            raise ValueError("unsupported PandaScore game")
        by_id: dict[str, tuple[FixtureRecord, ResultRecord | None]] = {}
        categories = ("upcoming", "past") if include_past else ("upcoming",)
        for category in categories:
            path = f"/{GAME_PATH[game]}/matches/{category}"
            for page in range(1, self.max_pages + 1):
                try:
                    response = self.client.get(
                        self.base_url + path,
                        headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
                        params={"page[size]": self.page_size, "page[number]": page},
                    )
                except httpx.RequestError as exc:
                    raise PandaScoreError("PandaScore transport unavailable") from exc
                if response.status_code == 429:
                    raise PandaScoreRateLimited("PandaScore rate limit reached")
                if response.status_code in (401, 403):
                    raise PandaScoreError("PandaScore account lacks access")
                if response.status_code >= 400:
                    raise PandaScoreError(f"PandaScore HTTP {response.status_code}")
                try:
                    rows = response.json()
                except ValueError as exc:
                    raise PandaScoreError("PandaScore response is not JSON") from exc
                if not isinstance(rows, list):
                    raise PandaScoreError("PandaScore response is not a match list")
                for raw in rows:
                    normalized = normalize_match(raw, game)
                    if normalized is None:
                        continue
                    fixture, result = normalized
                    prior = by_id.get(fixture.external_match_id)
                    if prior is None or fixture.source_updated_at > prior[0].source_updated_at:
                        by_id[fixture.external_match_id] = fixture, result
                    elif fixture.source_updated_at == prior[0].source_updated_at and fixture != prior[0]:
                        raise PandaScoreError("conflicting match versions at the same source time")
                if len(rows) < self.page_size:
                    break
                if response.headers.get("X-Rate-Limit-Remaining") == "0":
                    raise PandaScoreRateLimited("PandaScore request budget exhausted")
        ordered = [by_id[key] for key in sorted(by_id, key=int)]
        return FixtureImportDocument(
            fixtures=[item[0] for item in ordered],
            results=[item[1] for item in ordered if item[1] is not None],
        )
