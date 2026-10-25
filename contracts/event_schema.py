"""
UrbanPulse — Canonical Event Schema
=====================================
SCHEMA_VERSION = "1.0.0"

THIS FILE IS THE INTERFACE CONTRACT between all four team members.
Both teams import from here. Never change a field without agreement
from all four (Priyanshu, Kanak, Ashlesha, Sanvi).

Reconciled from:
  - kanak/contracts/event_schema.py   (full enums, validators, dedup_signature)
  - priyanshu/contracts/event_schema.py (Literal types, SOURCE_RELIABILITY dict)

Key decisions locked here:
  - source_type values: "official" | "sensor" | "crowdsourced" | "anonymous"
    (plan D10 uses "crowdsourced"; "crowd" is accepted as alias for compatibility)
  - h3_cell: res-9, 15 lowercase hex chars
  - scenario_tag: evaluation only, stripped on production ingest path
  - No PII fields. Parser scrubs content before creating events.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0.0"

# ── Source reliability tiers (plan D10 — locked) ──────────────────────────────
SOURCE_RELIABILITY: dict[str, float] = {
    "official":     0.9,
    "sensor":       0.7,
    "crowdsourced": 0.5,
    "crowd":        0.5,   # alias — accepted but normalised to "crowdsourced"
    "anonymous":    0.3,
}

# ── PII detection ─────────────────────────────────────────────────────────────
_PII_PATTERNS = [
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),          # phone numbers
    re.compile(r"\b[6-9]\d{9}\b"),                               # Indian mobiles
    re.compile(r"\b\d{12}\b"),                                   # Aadhaar
    re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),                      # PAN card
    re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),  # email
    re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
               r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),           # UUID device IDs
    re.compile(r"\b(Mr|Mrs|Ms|Dr|Sir|Prof)\b", re.IGNORECASE),  # name titles
]

_FORBIDDEN_FIELDS = frozenset({
    "name", "full_name", "first_name", "last_name",
    "phone", "phone_number", "mobile", "contact",
    "email", "address", "device_id", "imei", "mac_address",
    "user_id", "person_id", "individual_id", "uid",
    "aadhaar", "pan", "passport", "driving_licence",
    "ip_address", "gps_lat", "gps_lon", "exact_location",
})


def has_pii(text: str) -> bool:
    """Return True if the string matches any known PII pattern."""
    return bool(text) and any(p.search(text) for p in _PII_PATTERNS)


# ── Canonical Event ────────────────────────────────────────────────────────────

class CanonicalEvent(BaseModel):
    """
    The single shared data structure that flows through the entire system.

    Domains  : power | transit | water | health | comms | road
    source_type: official | sensor | crowdsourced | anonymous
                 ("crowd" is accepted and normalised to "crowdsourced")
    """

    event_id:            str   = Field(default_factory=lambda: str(uuid.uuid4()))
    domain:              str   = Field(..., pattern=r"^(power|transit|water|health|comms|road)$")
    event_type:          str   = Field(..., min_length=1, max_length=64)
    entity_id:           str   = Field(..., min_length=1, max_length=128,
                                       description="Infrastructure ID — NO personal identifiers")
    h3_cell:             str   = Field(..., description="H3 res-9 cell (15 lowercase hex chars)")
    severity:            float = Field(..., ge=0.0, le=1.0)
    source_type:         str   = Field(..., description="official|sensor|crowdsourced|anonymous")
    source_reliability:  float = Field(..., ge=0.0, le=1.0)
    event_timestamp:     datetime
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    parse_confidence:    float = Field(default=1.0, ge=0.0, le=1.0)
    scenario_tag:        Optional[str] = Field(
        default=None, max_length=128,
        description="Eval only — NEVER read in the production scoring path"
    )

    model_config = {"str_strip_whitespace": True, "strict": False}

    # ── Validators ────────────────────────────────────────────────────────────

    @model_validator(mode="before")
    @classmethod
    def reject_forbidden_fields(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        found = _FORBIDDEN_FIELDS.intersection(data.keys())
        if found:
            raise ValueError(
                f"Forbidden PII field(s) in request: {sorted(found)}"
            )
        return data

    @field_validator("source_type", mode="before")
    @classmethod
    def normalise_source_type(cls, v: str) -> str:
        """Accept 'crowd' as alias for 'crowdsourced'."""
        if v == "crowd":
            return "crowdsourced"
        if v not in SOURCE_RELIABILITY:
            raise ValueError(
                f"source_type must be one of {list(SOURCE_RELIABILITY.keys())}"
            )
        return v

    @field_validator("source_reliability", mode="before")
    @classmethod
    def auto_reliability(cls, v, info):
        """Auto-set reliability from source_type if not explicitly provided."""
        data = info.data if hasattr(info, "data") else {}
        src = data.get("source_type", "")
        # If caller passed 0.5 (Pydantic default) and source_type is known, use tier
        if v == 0.5 and src in SOURCE_RELIABILITY:
            return SOURCE_RELIABILITY[src]
        return v

    @field_validator("h3_cell")
    @classmethod
    def valid_h3(cls, v: str) -> str:
        v = v.lower()
        if len(v) != 15 or not all(c in "0123456789abcdef" for c in v):
            raise ValueError(
                f"Invalid H3 res-9 cell ID: {v!r} (must be 15 hex chars)"
            )
        return v

    @field_validator("event_type")
    @classmethod
    def lowercase_event_type(cls, v: str) -> str:
        return v.lower()

    @field_validator("entity_id", "event_type")
    @classmethod
    def no_pii_in_fields(cls, v: str) -> str:
        if has_pii(v):
            raise ValueError(f"PII detected in field: {v[:40]}...")
        return v

    @field_validator("event_timestamp")
    @classmethod
    def timestamp_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("event_timestamp must be timezone-aware (UTC).")
        return v

    # ── Helpers ───────────────────────────────────────────────────────────────

    def dedup_signature(self) -> str:
        """
        Deduplication key: (domain, event_type, entity_id, H3 res-8 parent, 1-hour bucket).
        Returns an 8-char hex digest. Never reversible to any individual.
        """
        try:
            import h3
            parent = h3.cell_to_parent(self.h3_cell, 8)
        except Exception:
            parent = self.h3_cell[:13]

        bucket = self.event_timestamp.strftime("%Y%m%d%H")
        raw = f"{self.domain}|{self.event_type}|{self.entity_id}|{parent}|{bucket}"
        return hashlib.sha256(raw.encode()).hexdigest()[:8]

    def for_production(self) -> "CanonicalEvent":
        """Return a copy with scenario_tag stripped (production ingest path)."""
        return self.model_copy(update={"scenario_tag": None})


# ── Ingest request wrapper ─────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    """
    Wrapper for POST /ingest.
    Accepts exactly one of: a structured event, raw text, or a batch.
    """
    event:    Optional[CanonicalEvent]       = None
    raw_text: Optional[str]                  = Field(default=None, max_length=512)
    batch:    Optional[list[CanonicalEvent]] = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def exactly_one(self) -> "IngestRequest":
        n = sum([self.event is not None,
                 self.raw_text is not None,
                 self.batch is not None])
        if n != 1:
            raise ValueError("Provide exactly one of: 'event', 'raw_text', or 'batch'.")
        return self

    @field_validator("raw_text")
    @classmethod
    def raw_text_no_pii(cls, v: Optional[str]) -> Optional[str]:
        if v and has_pii(v):
            raise ValueError(
                "raw_text contains PII. Node parser must scrub before submitting."
            )
        return v
