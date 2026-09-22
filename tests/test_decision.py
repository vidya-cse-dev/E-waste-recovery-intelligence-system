"""Unit tests for the decision rules and the value estimator."""
from decision import decide, severity_band
from value import estimate


def cond(severity=0.0, confidence=0.85, findings=None):
    return {"severity": severity, "confidence": confidence, "findings": findings or {}}


def test_severity_bands():
    assert severity_band(0.0) == "none"
    assert severity_band(0.3) == "minor"
    assert severity_band(0.6) == "moderate"
    assert severity_band(0.9) == "severe"


def test_battery_swelling_is_always_recycle():
    d = decide("battery", cond(), {"bat_swelling": "yes", "bat_charge": "works"})
    assert d["code"] == "recycle"


def test_clean_battery_without_answers_needs_testing():
    d = decide("battery", cond(), {})
    assert d["code"] == "testing"


def test_healthy_battery_that_works_is_reusable():
    d = decide("battery", cond(), {"bat_swelling": "no", "bat_charge": "works", "bat_age": "lt1"})
    assert d["code"] == "reusable"


def test_old_battery_is_downgraded_to_testing():
    d = decide("battery", cond(), {"bat_swelling": "no", "bat_charge": "works", "bat_age": "gt3"})
    assert d["code"] == "testing"


def test_dead_battery_is_recycled_not_repaired():
    d = decide("battery", cond(), {"bat_swelling": "no", "bat_charge": "dead"})
    assert d["code"] == "recycle"


def test_clean_arduino_that_works_is_reusable():
    d = decide("arduino", cond(), {"ard_power": "yes", "ard_upload": "yes", "ard_pins": "no"})
    assert d["code"] == "reusable"


def test_clean_arduino_without_answers_is_potentially_reusable():
    assert decide("arduino", cond(), {})["code"] == "reusable"


def test_arduino_with_damaged_pins_is_repairable():
    d = decide("arduino", cond(0.3, findings={"burn": 0.4}), {"ard_power": "yes", "ard_pins": "yes"})
    assert d["code"] == "repairable"


def test_dead_arduino_is_repairable():
    assert decide("arduino", cond(), {"ard_power": "no"})["code"] == "repairable"


def test_severe_damage_is_recycle():
    d = decide("motor", cond(0.85, findings={"burn": 0.95}), {})
    assert d["code"] == "recycle"


def test_severe_damage_but_works_is_conflict_and_needs_testing():
    d = decide("motor", cond(0.85, findings={"burn": 0.95}), {"mot_spin": "smooth"})
    assert d["code"] == "testing"


def test_moderate_damage_unknown_function_needs_testing():
    assert decide("sensor", cond(0.6, findings={"corrosion": 0.9}), {})["code"] == "testing"


def test_capacitor_bulging_is_recycle():
    assert decide("capacitor", cond(), {"cap_bulge": "yes"})["code"] == "recycle"


def test_low_detection_confidence_blocks_reuse_without_answers():
    assert decide("arduino", cond(), {}, det_conf=0.3)["code"] == "testing"


def test_unknown_component_uses_generic_questions():
    d = decide("relay", cond(), {"gen_works": "yes", "gen_damage": "no", "gen_hazard": "no"})
    assert d["code"] == "reusable"


def test_certainty_is_capped_when_testing_is_needed():
    d = decide("battery", cond(confidence=0.95), {})
    assert d["code"] == "testing" and d["certainty"] <= 0.6


def test_value_ordering_reuse_beats_recycle():
    reuse = estimate("arduino", "reusable")["estimate"]
    recycle = estimate("arduino", "recycle")["estimate"]
    assert reuse > recycle > 0


def test_value_range_is_consistent():
    for code in ("reusable", "repairable", "recycle", "testing"):
        v = estimate("motor", code, severity=0.3)
        assert v["low"] <= v["estimate"] <= v["high"]


def test_hazardous_recycle_pays_less():
    assert estimate("battery", "recycle", hazard=True)["estimate"] < estimate("battery", "recycle")["estimate"]
