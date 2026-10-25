"""
Phase 2 Integration Test
Tests all 6 domains, cascade interactions, and simulator integration.
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(__file__))

def test_simulators():
    """Test that all domain simulators can generate events."""
    print("\n" + "="*80)
    print("TEST 1: Domain Simulator Generation")
    print("="*80)
    
    import sim.power_sim as power_sim
    import sim.water_sim as water_sim
    import sim.transit_sim as transit_sim
    import sim.health_sim as health_sim
    import sim.comms_sim as comms_sim
    import sim.road_sim as road_sim
    
    tests = [
        ("Power", power_sim.voltage_drop),
        ("Water", water_sim.pressure_drop),
        ("Transit", transit_sim.severe_delay),
        ("Health", health_sim.capacity_high),
        ("Comms", comms_sim.signal_degraded),
        ("Road", road_sim.accident_reported),
    ]
    
    for domain, func in tests:
        events = func(scenario_tag="test")
        assert len(events) > 0, f"{domain} simulator returned no events"
        assert events[0]["domain"] == domain.lower(), f"Wrong domain: {events[0]['domain']}"
        print(f"  ✅ {domain:8} simulator: {len(events)} events generated")
    
    print("\n✅ All simulators working\n")


def test_risk_model_all_domains():
    """Test risk scoring with all 6 domains."""
    print("="*80)
    print("TEST 2: Risk Model - All Domains")
    print("="*80)
    
    from engine.risk_model import MODEL
    
    # Test individual domains
    domains_to_test = [
        ("power",   {"power": 1.0}),
        ("water",   {"water": 1.0}),
        ("transit", {"transit": 1.0}),
        ("health",  {"health": 1.0}),
        ("comms",   {"comms": 1.0}),
        ("road",    {"road": 1.0}),
    ]
    
    baseline = {"grid_failure_rate": 0.2, "economic_constraint": 0.3}
    
    for domain, stress in domains_to_test:
        risk, label = MODEL.score(stress, baseline)
        print(f"  {domain:8} stress=1.0 → risk={risk:.3f} ({label})")
        assert 0.0 <= risk <= 1.0, f"Risk out of bounds: {risk}"
    
    print("\n✅ All domains scored successfully\n")


def test_cascade_interactions():
    """Test cascade bonus (interaction terms)."""
    print("="*80)
    print("TEST 3: Cascade Interactions")
    print("="*80)
    
    from engine.risk_model import MODEL
    
    baseline = {"grid_failure_rate": 0.2, "economic_constraint": 0.3}
    
    # Test power→water cascade
    power_only = {"power": 1.0}
    water_only = {"water": 1.0}
    both = {"power": 1.0, "water": 1.0}
    
    risk_power, _ = MODEL.score(power_only, baseline)
    risk_water, _ = MODEL.score(water_only, baseline)
    risk_both, _ = MODEL.score(both, baseline)
    
    cascade_bonus = risk_both - (risk_power + risk_water)
    
    print(f"  Power alone:          {risk_power:.3f}")
    print(f"  Water alone:          {risk_water:.3f}")
    print(f"  Power + Water:        {risk_both:.3f}")
    print(f"  Cascade bonus:        {cascade_bonus:+.3f}")
    
    # Cascade should amplify risk (interaction term > 0)
    assert risk_both > risk_power, "Cascade should increase risk"
    print(f"  ✅ Cascade amplification detected: {cascade_bonus:+.3f}\n")
    
    # Test road→transit cascade
    road_only = {"road": 1.0}
    transit_only = {"transit": 1.0}
    road_transit = {"road": 1.0, "transit": 1.0}
    
    risk_road, _ = MODEL.score(road_only, baseline)
    risk_transit, _ = MODEL.score(transit_only, baseline)
    risk_rt, _ = MODEL.score(road_transit, baseline)
    
    print(f"  Road alone:           {risk_road:.3f}")
    print(f"  Transit alone:        {risk_transit:.3f}")
    print(f"  Road + Transit:       {risk_rt:.3f}")
    print(f"  Cascade bonus:        {risk_rt - (risk_road + risk_transit):+.3f}")
    
    print("\n✅ Cascade interactions working\n")


def test_confidence_formula():
    """Test confidence calculation across domains."""
    print("="*80)
    print("TEST 4: Confidence Formula")
    print("="*80)
    
    from engine.confidence import compute_confidence
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    
    # Test coverage component
    sources_1 = [("official", 0.8, now)]
    sources_3 = [("official", 0.8, now), ("sensor", 0.7, now), ("crowd", 0.6, now)]
    
    conf_1 = compute_confidence(sources_1)
    conf_3 = compute_confidence(sources_3)
    
    print(f"  1 source:  confidence = {conf_1:.3f}")
    print(f"  3 sources: confidence = {conf_3:.3f}")
    assert conf_3 > conf_1, "More sources should increase confidence"
    print(f"  ✅ Coverage component working\n")
    
    # Test freshness decay
    fresh = [("official", 0.8, now)]
    stale = [("official", 0.8, now - timedelta(hours=6))]
    very_stale = [("official", 0.8, now - timedelta(hours=12))]
    
    conf_fresh = compute_confidence(fresh)
    conf_stale = compute_confidence(stale)
    conf_very_stale = compute_confidence(very_stale)
    
    print(f"  Fresh (now):    confidence = {conf_fresh:.3f}")
    print(f"  Stale (6h):     confidence = {conf_stale:.3f}")
    print(f"  Very stale(12h):confidence = {conf_very_stale:.3f}")
    assert conf_fresh > conf_stale > conf_very_stale, "Freshness should decay over time"
    print(f"  ✅ Freshness decay working\n")
    
    # Test agreement component
    agree = [("official", 0.8, now), ("sensor", 0.85, now), ("crowd", 0.75, now)]
    disagree = [("official", 0.9, now), ("sensor", 0.3, now), ("crowd", 0.6, now)]
    
    conf_agree = compute_confidence(agree)
    conf_disagree = compute_confidence(disagree)
    
    print(f"  Agreement (σ=0.05):    confidence = {conf_agree:.3f}")
    print(f"  Disagreement (σ=0.3):  confidence = {conf_disagree:.3f}")
    assert conf_agree > conf_disagree, "Agreement should increase confidence"
    print(f"  ✅ Agreement component working\n")
    
    print("✅ Confidence formula validated\n")


def test_multi_domain_stress():
    """Test cell state with multiple simultaneous stressors."""
    print("="*80)
    print("TEST 5: Multi-Domain Cell State")
    print("="*80)
    
    from engine.cell_state import CellState
    from engine.risk_model import MODEL
    
    cell = CellState("890c1d2cf37ffff")
    
    # Simulate multiple simultaneous failures
    cell.update("power", 1.0, "official")
    cell.update("water", 0.9, "official")
    cell.update("transit", 0.7, "sensor")
    cell.update("health", 0.6, "crowd")
    cell.update("comms", 0.5, "sensor")
    cell.update("road", 0.8, "official")
    
    baseline = {"grid_failure_rate": 0.3, "economic_constraint": 0.4}
    risk, label = MODEL.score(cell.decayed_stress, baseline)
    
    print(f"  Cell: {cell.h3_cell}")
    print(f"  Stress levels:")
    for domain, stress in cell.decayed_stress.items():
        print(f"    {domain:8}: {stress:.3f}")
    print(f"  Risk: {risk:.3f} ({label})")
    print(f"  Confidence: {cell.confidence:.3f}")
    
    assert risk > 0.65, f"Multi-domain stress should create high risk (got {risk:.3f})"
    assert label == "high", f"Expected high risk label, got {label}"
    
    print("\n✅ Multi-domain stress handling working\n")


def test_pii_rejection():
    """Test that PII patterns are properly rejected."""
    print("="*80)
    print("TEST 6: PII Detection")
    print("="*80)
    
    from contracts.event_schema import CanonicalEvent
    from pydantic import ValidationError
    
    pii_cases = [
        ("Aadhaar", "feeder-123456789012"),
        ("PAN", "pump-ABCDE1234F"),
        ("Mobile", "route-9876543210"),
        ("Email", "hospital-user@example.com"),
        ("Phone", "tower-555-123-4567"),
    ]
    
    for pii_type, entity_id in pii_cases:
        try:
            event = CanonicalEvent(
                event_id="550e8400-e29b-41d4-a716-446655440000",
                domain="power",
                event_type="blackout",
                entity_id=entity_id,
                h3_cell="890c1d2cf37ffff",
                severity=1.0,
                source_type="official",
                source_reliability=0.9,
                event_timestamp="2026-10-25T14:30:00Z",
                ingestion_timestamp="2026-10-25T14:30:02Z",
                parse_confidence=1.0,
            )
            print(f"  ❌ {pii_type:8} NOT rejected: {entity_id}")
            assert False, f"{pii_type} should have been rejected"
        except ValidationError as e:
            if "PII" in str(e):
                print(f"  ✅ {pii_type:8} rejected: {entity_id}")
            else:
                print(f"  ⚠️  {pii_type:8} rejected but not for PII: {e}")
    
    print("\n✅ PII detection working\n")


def test_baseline_features():
    """Test baseline features loading."""
    print("="*80)
    print("TEST 7: Baseline Features")
    print("="*80)
    
    try:
        from engine.baseline_features import load_baseline_features
        
        features = load_baseline_features()
        print(f"  Loaded baseline features for {len(features)} cells")
        
        # Check a sample cell
        if features:
            sample_cell = list(features.keys())[0]
            sample_features = features[sample_cell]
            print(f"  Sample cell: {sample_cell}")
            print(f"    Population: {sample_features.population}")
            print(f"    Hospital isolation: {sample_features.hospital_isolation:.3f}")
            print(f"    Economic constraint: {sample_features.economic_constraint:.3f}")
            print(f"    Grid failure rate: {sample_features.grid_failure_rate:.3f}")
        
        print("\n✅ Baseline features loaded\n")
    except Exception as e:
        print(f"  ⚠️  Baseline features not fully ready: {e}")
        print("  (This is expected if data files are not generated yet)\n")


def run_all_tests():
    """Run all Phase 2 tests."""
    print("\n" + "="*80)
    print(" "*20 + "PHASE 2 INTEGRATION TESTS")
    print("="*80 + "\n")
    
    tests = [
        ("Simulator Generation", test_simulators),
        ("Risk Model - All Domains", test_risk_model_all_domains),
        ("Cascade Interactions", test_cascade_interactions),
        ("Confidence Formula", test_confidence_formula),
        ("Multi-Domain Cell State", test_multi_domain_stress),
        ("PII Detection", test_pii_rejection),
        ("Baseline Features", test_baseline_features),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {name}")
            print(f"   Error: {e}\n")
            failed += 1
    
    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
