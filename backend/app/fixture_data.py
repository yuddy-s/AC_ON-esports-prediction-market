"""Provider-independent M4 fixture and result records.

These records are off-chain source data. They do not register fixtures or settle markets.
"""

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


SOURCE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
HASH_32 = re.compile(r"^0x[0-9a-fA-F]{64}$")
FixtureStatus = Literal["scheduled", "live", "postponed", "completed", "canceled", "tied", "no_contest", "unsupported"]
ResultStatus = Literal["completed", "canceled", "tied", "no_contest", "unsupported"]


class SourceIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(min_length=1, max_length=80)
    game_id: str = Field(min_length=1, max_length=80)
    external_match_id: str = Field(min_length=1, max_length=160)

    @field_validator("provider_id", "game_id", "external_match_id")
    @classmethod
    def valid_source_id(cls, value: str) -> str:
        if not SOURCE_ID.fullmatch(value):
            raise ValueError("source identifiers must use ASCII letters, numbers, period, underscore, colon, or hyphen")
        return value

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.provider_id, self.game_id, self.external_match_id


class FixtureRecord(SourceIdentity):
    scheduled_start: datetime
    match_status: FixtureStatus
    team_a_id: str = Field(min_length=1, max_length=160)
    team_a_name: str = Field(min_length=1, max_length=160)
    team_b_id: str = Field(min_length=1, max_length=160)
    team_b_name: str = Field(min_length=1, max_length=160)
    evidence_url: HttpUrl | None = None
    evidence_hash: str | None = None
    source_updated_at: datetime

    @field_validator("team_a_id", "team_b_id", "team_a_name", "team_b_name")
    @classmethod
    def nonblank_team(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("team IDs and names cannot be blank")
        return stripped

    @field_validator("scheduled_start", "source_updated_at")
    @classmethod
    def aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def distinct_teams(self) -> "FixtureRecord":
        if self.team_a_id == self.team_b_id:
            raise ValueError("Team A and Team B must have distinct IDs")
        if (self.evidence_url is None) != (self.evidence_hash is None):
            raise ValueError("fixture evidence_url and evidence_hash must be supplied together")
        return self

    @field_validator("evidence_hash")
    @classmethod
    def valid_hash(cls, value: str | None) -> str | None:
        if value is not None and not HASH_32.fullmatch(value):
            raise ValueError("evidence_hash must be a 0x-prefixed 32-byte hex digest")
        return value.lower() if value is not None else None


class ResultRecord(SourceIdentity):
    match_status: ResultStatus
    winner_team_id: str | None = Field(default=None, max_length=160)
    source_updated_at: datetime
    evidence_url: HttpUrl
    evidence_hash: str

    @field_validator("source_updated_at")
    @classmethod
    def aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone")
        return value.astimezone(UTC)

    @field_validator("evidence_hash")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        if not HASH_32.fullmatch(value):
            raise ValueError("evidence_hash must be a 0x-prefixed 32-byte hex digest")
        return value.lower()

    @model_validator(mode="after")
    def valid_winner(self) -> "ResultRecord":
        if self.match_status == "completed" and not self.winner_team_id:
            raise ValueError("completed results require winner_team_id")
        if self.match_status != "completed" and self.winner_team_id is not None:
            raise ValueError("VOID-type results cannot name a winner")
        return self


class FixtureImportDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixtures: list[FixtureRecord] = Field(default_factory=list)
    results: list[ResultRecord] = Field(default_factory=list)


def load_manual_json(path: str | Path) -> FixtureImportDocument:
    """Load an operator-controlled JSON file; never fetch or trust a public write request."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return FixtureImportDocument.model_validate(data)


def deterministic_mock() -> FixtureImportDocument:
    """Stable, explicitly fictional data for automated tests and local demos."""
    return FixtureImportDocument.model_validate(
        {
            "fixtures": [
                {
                    "provider_id": "acon-mock",
                    "game_id": "valorant",
                    "external_match_id": "demo-final-1",
                    "scheduled_start": "2030-01-01T18:00:00Z",
                    "match_status": "completed",
                    "team_a_id": "alpha",
                    "team_a_name": "Mock Alpha",
                    "team_b_id": "bravo",
                    "team_b_name": "Mock Bravo",
                    "evidence_url": "https://example.org/acon-mock/demo-final-1-schedule",
                    "evidence_hash": "0x" + "00" * 32,
                    "source_updated_at": "2030-01-01T21:00:00Z",
                }
            ],
            "results": [
                {
                    "provider_id": "acon-mock",
                    "game_id": "valorant",
                    "external_match_id": "demo-final-1",
                    "match_status": "completed",
                    "winner_team_id": "alpha",
                    "source_updated_at": "2030-01-01T21:00:00Z",
                    "evidence_url": "https://example.org/acon-mock/demo-final-1",
                    "evidence_hash": "0x" + "11" * 32,
                }
            ],
        }
    )
