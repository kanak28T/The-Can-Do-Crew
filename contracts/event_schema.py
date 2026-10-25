"""
UrbanPulse Canonical Event Schema
SCHEMA_VERSION = "1.0.0"

THIS IS THE BLOCKER FILE. All team members import from here.
No PII fields allowed. Parser scrubs content before creating events.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
import re

SCHEMA_VERSION = "1.0.0"

# PII patterns to reject
_PHONE_RE    = re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b')
_EMAIL_RE    = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
_DEVICE_RE   = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')
_NAME_TITLE  = re.compile(r'\b(Mr|Mrs|Ms|Dr|Sir|Prof)\b', re.IGNORECASE)


def _has_pii(value: str) -> bool:
    return bool(
        _PHONE_RE.search(value) or
        _EMAIL_RE.search(value) or
        _DEVICE_RE.search(value) or
        _NAME_TITLE.search(value)
    )


class CanonicalEvent(BaseModel):
    """
    Canonical event. Strict. No PII.
    All domains: power | transit | water | health | comms | road
    """

    event_id:            str     = Field(..., description="UUID of the event")
    domain:              Literal["power", "transit", "water", "health", "comms", "road"]
    event_type:          str     = Field(..., min_length=1, max_length=64)
    entity_id:           str     = Field(..., min_length=1, max_length=128,
                                         description="Feeder/route/road/pump/tower/hospital ID — NO personal identifiers")
    h3_cell:             str     = Field(..., description="H3 resolution-9 cell ID (15 hex chars)")
    severity:            float   = Field(..., ge=0.0, le=1.0)
    source_type:         Literal["official", "sensor", "crowd", "anonymous"]
    source_reliability:  float   = Field(..., ge=0.0, le=1.0)
    event_timestamp:     datetime
    ingestion_timestamp: datetime
    parse_confidence:    float   = Field(..., ge=0.0, le=1.0)
    scenario_tag:        Optional[str] = Field(None, max_length=128,
                                               description="Eval use only — NEVER read in production scoring path")

    model_config = {"strict": False}   # allow datetime strings from JSON

    @field_validator("entity_id", "event_type")
    @classmethod
    def no_pii(cls, v: str) -> str:
        if _has_pii(v):
            raise ValueError(f"PII detected in field value: {v[:40]}...")
        return v

    @field_validator("h3_cell")
    @classmethod
    def valid_h3(cls, v: str) -> str:
        if len(v) != 15 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError(f"Invalid H3 res-9 cell ID: {v}")
        return v.lower()

    @field_validator("event_type")
    @classmethod
    def lowercase_type(cls, v: str) -> str:
        return v.lower()


# Source reliability tiers (D10 — locked)
SOURCE_RELIABILITY = {
    "official":  0.9,
    "sensor":    0.7,
    "crowd":     0.5,
    "anonymous": 0.3,
}
