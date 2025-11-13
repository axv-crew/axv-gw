"""Pydantic schemas for status responses."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ServiceState(str, Enum):
    """Service state enumeration."""

    OK = "ok"
    WARN = "warn"
    DOWN = "down"
    UNKNOWN = "unknown"


class ServiceStatus(BaseModel):
    """Individual service status."""

    id: str = Field(..., description="Unique service identifier")
    label: str = Field(..., description="Human-readable service label")
    state: ServiceState = Field(..., description="Current service state")
    note: str | None = Field(None, description="Optional status note")


class FrontStatusV1(BaseModel):
    """Frontend status response contract v1."""

    updated_at: datetime = Field(
        ..., alias="updatedAt", description="Timestamp of last status update (ISO 8601)"
    )
    services: list[ServiceStatus] = Field(..., description="List of service statuses")

    model_config = {"populate_by_name": True}
