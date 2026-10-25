"""
Phase 0 test — runs without a server.
Tests schema validation and PII rejection directly.
Run: python test_phase0.py
"""
import sys
sys.path.insert(0, ".")

from contracts.event_schema import CanonicalEvent, SCHEMA_VERSION
from pydantic import ValidationError
from datetime import datetime, timezone

print(f"Schema version: {SCHEMA_VERSION}\n")

# ── Test 1: valid event ───────────────────────────────────────────────────────
try:
    e = CanonicalEvent(
        event_id            = "550e8400-e29b-41d4-a716-446655440000",
        domain              = "power",
        event_type          = "blackout",
        entity_id           = "feeder-F12",
        h3_cell             = "890c1d2cf37ffff",
        severity            = 1.0,
        source_type         = "official",
        source_reliability  = 0.9,
        event_timestamp     = datetime(2026, 10, 25, 14, 30, 0, tzinfo=timezone.utc),
        ingestion_timestamp = datetime(2026, 10, 25, 14, 30, 2, tzinfo=timezone.utc),
        parse_confidence    = 1.0,
    )
    print("✅ Test 1 PASS — valid event accepted:", e.event_id)
except Exception as ex:
    print("❌ Test 1 FAIL:", ex)

# ── Test 2: PII in entity_id ──────────────────────────────────────────────────
try:
    e = CanonicalEvent(
        event_id            = "550e8400-e29b-41d4-a716-446655440001",
        domain              = "road",
        event_type          = "closure",
        entity_id           = "Mr. John 555-123-4567",
        h3_cell             = "890c1d2cf37ffff",
        severity            = 0.8,
        source_type         = "crowd",
        source_reliability  = 0.5,
        event_timestamp     = datetime(2026, 10, 25, 14, 30, 0, tzinfo=timezone.utc),
        ingestion_timestamp = datetime(2026, 10, 25, 14, 30, 2, tzinfo=timezone.utc),
        parse_confidence    = 0.7,
    )
    print("❌ Test 2 FAIL — PII should have been rejected")
except ValidationError:
    print("✅ Test 2 PASS — PII rejected correctly")

# ── Test 3: invalid domain ────────────────────────────────────────────────────
try:
    e = CanonicalEvent(
        event_id            = "550e8400-e29b-41d4-a716-446655440002",
        domain              = "fire",   # not a valid domain
        event_type          = "alert",
        entity_id           = "station-01",
        h3_cell             = "890c1d2cf37ffff",
        severity            = 0.5,
        source_type         = "official",
        source_reliability  = 0.9,
        event_timestamp     = datetime(2026, 10, 25, 14, 30, 0, tzinfo=timezone.utc),
        ingestion_timestamp = datetime(2026, 10, 25, 14, 30, 2, tzinfo=timezone.utc),
        parse_confidence    = 1.0,
    )
    print("❌ Test 3 FAIL — invalid domain should be rejected")
except ValidationError:
    print("✅ Test 3 PASS — invalid domain rejected correctly")

# ── Test 4: severity out of range ─────────────────────────────────────────────
try:
    e = CanonicalEvent(
        event_id            = "550e8400-e29b-41d4-a716-446655440003",
        domain              = "transit",
        event_type          = "suspension",
        entity_id           = "route-4",
        h3_cell             = "890c1d2cf37ffff",
        severity            = 1.5,   # > 1.0
        source_type         = "crowd",
        source_reliability  = 0.5,
        event_timestamp     = datetime(2026, 10, 25, 14, 30, 0, tzinfo=timezone.utc),
        ingestion_timestamp = datetime(2026, 10, 25, 14, 30, 2, tzinfo=timezone.utc),
        parse_confidence    = 0.8,
    )
    print("❌ Test 4 FAIL — severity > 1.0 should be rejected")
except ValidationError:
    print("✅ Test 4 PASS — out-of-range severity rejected correctly")

print("\nAll Phase 0 tests done.")
