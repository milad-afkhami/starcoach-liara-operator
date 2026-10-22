from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Target(Record):
    model_config = ConfigDict(extra="forbid", frozen=True)
    team_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    app_name: str = Field(min_length=1, max_length=63, pattern=r"^[a-z0-9][a-z0-9-]*$")
    app_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    origin: str | None = None


class ServiceSummary(Record):
    target: Target
    platform: str
    runtime_state: str
    last_release_id: str | None = None
    observed_at: float
    capabilities: dict = Field(default_factory=dict)


class Evidence(Record):
    id: str
    target: Target
    kind: str
    observed_at: float
    available_at: float
    quality: Literal["fresh", "stale", "unavailable", "invalid"]
    redacted_payload: dict
    coverage: dict = Field(default_factory=dict)
