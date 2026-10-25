"""
UrbanPulse — Canonical Event Schema
====================================
Version: 1.0   (bump SCHEMA_VERSION for any field change; notify all 4 members)

THIS FILE IS THE INTERFACE CONTRACT between Team Alpha (backend) and Team Beta
(data / frontend). Both teams import from here. Never change a field without
agreement from all four team members.

Design constraints (from plan section 3):
- No PII: no name, phone, device_id or free-text field that could carry PII.
- The node parser scrubs content BEFORE populating these fields.
- scenario_tag is evaluation-only and is stripped on the production ingest path.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Version ──────────────────────────────────────────────────────────────────
SCHEMA_VERSION = "1.0"


# ── Enumerations ──────────────────────────────────────────────────────────────

class Domain(str, Enum):
    transport    = "transport"
    power        = "power"
    water        = "water"
    health       = "health"
    roads        = "roads"
    comms        = "comms"


class EventType(str, Enum):
    # Transport
    transit_suspension  = "transit_suspension"
    road_closure        = "road_closure"
    road_open           = "road_open"
    transit_restored    = "transit_restored"
    # Power
    voltage_drop        = "voltage_drop"
    blackout            = "blackout"
    power_restored      = "power_restored"
    # Water
    pump_failure        = "pump_failure"
    pressure_drop       = "pressure_drop"
    water_restored      = "water_restored"
    # Health
    hospital_load_high  = "hospital_load_high"
    clinic_closed       = "clinic_closed"
    # Communications
    call_drop_spike     = "call_drop_spike"
    tower_down          = "tower_down"
    # Generic / unknown (parsed from unstructured text with low confidence)
    unknown             = "unknown"


class SourceType(str, Enum):
    official     = "official"     # Government / utility feed. Reliability tier: 0.9
    sensor       = "sensor"       # IoT / automated sensor.  Reliability tier: 0.7
    crowdsourced = "crowdsourced" # Verified crowd platform.  Reliability tier: 0.5
    anonymous    = "anonymous"    # Unverified / anonymous.   Reliability tier: 0.3


# Static reliability tiers (plan section D10)
SOURCE_RELIABILITY: dict[SourceType, float] = {
    SourceType.official:     0.9,
    SourceType.sensor:       0.7,
    SourceType.crowdsourced: 0.5,
    SourceType.anonymous:    0.3,
}


# ── PII patterns to reject / scrub ────────────────────────────────────────────
# Used both in the validator below and in node/text_parser.py

_PII_PATTERNS = [
    re.compile(r"\b\d{10}\b"),                          # 10-digit phone numbers
    re.compile(r"\b[6-9]\d{9}\b"),                      # Indian mobile numbers
    re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b"),    # US-style phone
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),              # Aadhaar / PAN-like patterns
    re.compile(r"\b\d{12}\b"),                           # 12-digit Aadhaar numbers
    re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    ),                                                   # Email addresses
]

_FORBIDDEN_FIELD_NAMES = frozenset({
    "name", "full_name", "first_name", "last_name",
    "phone", "phone_number", "mobile", "contact",
    "email", "address", "device_id", "imei", "mac_address",
    "user_id", "person_id", "individual_id", "uid",
    "aadhaar", "pan", "passport", "driving_licence",
    "ip_address", "gps_lat", "gps_lon", "exact_location",
})


def contains_pii(text: str) -> bool:
    """Return True if the string matches any known PII pattern."""
    if not text:
        return False
    return any(pattern.search(text) for pattern in _PII_PATTERNS)


# ── Canonical Event ────────────────────────────────────────────────────────────

class CanonicalEvent(BaseModel):
    """
    The single shared data structure that flows through the entire system.

    Fields:
        event_id            UUID, auto-generated if not provided.
        domain              Which urban subsystem this event belongs to.
        event_type          The specific type of event within the domain.
        entity_id           The route / feeder / tower / road / pump affected.
                            Must NOT be a personal identifier. Use infra IDs only.
        h3_cell             H3 resolution-9 cell string where the event is located.
        severity            0.0 (no stress) to 1.0 (maximum stress).
        source_type         Where the event came from (determines base reliability).
        source_reliability  Overrides the static tier if the caller supplies one;
                            otherwise auto-set from source_type.
        event_timestamp     When the event occurred (UTC). Required.
        ingestion_timestamp When the API received the event (UTC). Auto-set.
        parse_confidence    Confidence that the parser correctly extracted this event.
                            1.0 = structured input, < 1.0 = parsed from free text.
        scenario_tag        EVALUATION ONLY. Stripped on the production ingest path.
                            Never used by the engine to make decisions.
    """

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    domain: Domain
    event_type: EventType
    entity_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Infrastructure ID (route, feeder, tower, road, pump). No PII.",
    )

    h3_cell: str = Field(
        ...,
        pattern=r"^[0-9a-f]{15}$",   # H3 res-9 cell strings are 15 hex chars
        description="H3 resolution-9 cell ID (15 hex characters).",
    )

    severity: float = Field(..., ge=0.0, le=1.0)

    source_type: SourceType
    source_reliability: float = Field(default=0.5, ge=0.0, le=1.0)

    event_timestamp: datetime
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    parse_confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    # Evaluation only — never read in the production path
    scenario_tag: Optional[str] = Field(default=None, exclude=False)

    model_config = {"str_strip_whitespace": True}

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("source_reliability", mode="before")
    @classmethod
    def auto_reliability_from_source_type(cls, v, info):
        """If source_reliability is not explicitly set, derive it from source_type."""
        # Pydantic v2: info.data has the already-validated fields
        if v == 0.5 and "source_type" in (info.data or {}):
            return SOURCE_RELIABILITY.get(info.data["source_type"], 0.5)
        return v

    @field_validator("entity_id")
    @classmethod
    def entity_id_no_pii(cls, v: str) -> str:
        if contains_pii(v):
            raise ValueError(
                "entity_id contains PII patterns. Use infrastructure IDs only."
            )
        # entity_id must not look like a personal name (basic heuristic)
        if v.lower() in _FORBIDDEN_FIELD_NAMES:
            raise ValueError(f"entity_id '{v}' is a forbidden field name.")
        return v

    @field_validator("event_timestamp")
    @classmethod
    def timestamp_must_be_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("event_timestamp must be timezone-aware (UTC).")
        return v

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: dict) -> dict:
        """Reject any request that includes a PII field name."""
        if not isinstance(data, dict):
            return data
        found = _FORBIDDEN_FIELD_NAMES.intersection(data.keys())
        if found:
            raise ValueError(
                f"Request contains forbidden PII field(s): {sorted(found)}. "
                "UrbanPulse accepts no personal data."
            )
        return data

    # ── Helpers ───────────────────────────────────────────────────────────────

    def dedup_signature(self) -> str:
        """
        Deduplication key: (domain, event_type, entity_id, H3 res-8 parent, 1-hour bucket).

        Uses the H3 res-8 PARENT of the cell (not res-9) and a 1-hour time bucket
        so that near-duplicate reports from different sources in the same area and
        hour are collapsed. We never use source identity for dedup.

        Returns an 8-char hex digest (not reversible to any individual).
        """
        try:
            import h3
            parent_cell = h3.cell_to_parent(self.h3_cell, 8)
        except Exception:
            parent_cell = self.h3_cell[:13]   # fallback if h3 not installed

        hour_bucket = self.event_timestamp.strftime("%Y%m%d%H")
        raw = f"{self.domain}|{self.event_type}|{self.entity_id}|{parent_cell}|{hour_bucket}"
        return hashlib.sha256(raw.encode()).hexdigest()[:8]

    def strip_scenario_tag(self) -> "CanonicalEvent":
        """Return a copy with scenario_tag set to None (for production path)."""
        return self.model_copy(update={"scenario_tag": None})


# ── Ingest request wrapper (what the API receives) ────────────────────────────

class IngestRequest(BaseModel):
    """
    Wrapper accepted by POST /ingest.

    Supports three input formats:
      - structured:    a pre-built CanonicalEvent JSON object
      - unstructured:  raw_text that the node parser will convert
      - batch:         a list of either of the above

    The API layer calls the appropriate adapter, then validates the result
    against CanonicalEvent before writing to the event log.
    """

    # Exactly one of these must be set
    event: Optional[CanonicalEvent] = None
    raw_text: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Unstructured text to be parsed. Max 512 chars to limit injection surface.",
    )
    batch: Optional[list[CanonicalEvent]] = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def exactly_one_input(self) -> "IngestRequest":
        set_fields = sum([
            self.event is not None,
            self.raw_text is not None,
            self.batch is not None,
        ])
        if set_fields != 1:
            raise ValueError(
                "Provide exactly one of: 'event', 'raw_text', or 'batch'."
            )
        return self

    @field_validator("raw_text")
    @classmethod
    def raw_text_no_pii(cls, v: Optional[str]) -> Optional[str]:
        """Reject raw_text that contains PII before it even reaches the parser."""
        if v and contains_pii(v):
            raise ValueError(
                "raw_text contains PII patterns. "
                "The node parser must scrub PII before submitting to /ingest."
            )
        return v
