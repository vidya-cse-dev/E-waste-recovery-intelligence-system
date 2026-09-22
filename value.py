"""Estimated recovery value in Indian rupees.

reuse_value     - what a working second-hand unit might fetch
material_value  - scrap / material-recovery value
The estimate is adjusted for condition, age and the recommended route, and is
returned as a low-high range because nobody can price a used part exactly.
"""
from components import get_component

BASIS = "Based on typical second-hand and scrap prices, adjusted for condition and age. Treat it as a guide, not a quote."


def estimate(component, code, severity=0.0, age_factor=1.0, hazard=False):
    info = get_component(component)
    reuse, material = info["reuse_value"], info["material_value"]
    condition_factor = 1 - 0.5 * min(1.0, max(0.0, severity))

    if code == "reusable":
        est, spread = reuse * condition_factor * age_factor, 0.15
    elif code == "repairable":
        est, spread = max(material, reuse * 0.7 * age_factor - info["repair_cost"]), 0.25
    elif code == "recycle":
        est, spread = material * (0.6 if hazard else 1.0), 0.20
    else:  # needs further testing: anything between scrap and reuse is possible
        low = material
        high = max(material, reuse * condition_factor * age_factor)
        return {"low": round(low), "high": round(high), "estimate": round((low + high) / 2), "basis": BASIS}

    return {
        "low": round(est * (1 - spread)),
        "high": round(est * (1 + spread)),
        "estimate": round(est),
        "basis": BASIS,
    }
