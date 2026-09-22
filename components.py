"""Component knowledge base.

Everything the decision and value stages need to know about a component type lives
here. To support a new class from your YOLO model, add one entry to COMPONENTS
(and, optionally, its questions in questions.py). Unknown classes fall back to DEFAULT.

Values are indicative second-hand / scrap prices in Indian rupees. They are
assumptions for the estimate, not market quotes: edit them to match your sources.
"""

COMPONENTS = {
    "battery": {
        "display": "Battery",
        "aliases": ["battery", "batteries", "li ion", "lipo", "18650", "cell"],
        "reuse_value": 250, "material_value": 40, "repair_cost": 0,
        "repairable": False, "safety_critical": True, "ages_out": True,
        "notes": {
            "reusable": "Check its capacity on a proper charger or battery tester before using it in a project. Never use a cell that swells or gets warm.",
            "repairable": "Cells cannot be repaired, but a healthy cell can be rebuilt into a new pack after testing.",
            "recycle": "Hand it to an authorised e-waste or battery collection point. Do not bin, puncture or burn it, and tape the terminals first.",
            "testing": "Measure its resting voltage, then run a charge and discharge test somewhere fire-safe. If it swells, warms up or loses charge fast, send it for recycling.",
        },
    },
    "arduino": {
        "display": "Arduino board",
        "aliases": ["arduino", "uno", "nano", "mega", "dev board", "microcontroller"],
        "reuse_value": 450, "material_value": 60, "repair_cost": 100,
        "repairable": True, "safety_critical": False, "ages_out": False,
        "notes": {
            "reusable": "Plug it in over USB, upload a blink sketch and test each pin group before reusing it.",
            "repairable": "Typical fixes: replace a burnt header, reflow a lifted pad, or swap the USB or regulator chip. Test after each fix.",
            "recycle": "Send it to an authorised e-waste recycler. The board contains recoverable copper, gold plating and solder.",
            "testing": "Check for shorts with a multimeter, then power it from a current-limited supply and try uploading a sketch.",
        },
    },
    "motor": {
        "display": "Motor",
        "aliases": ["motor", "dc motor", "servo", "stepper", "bldc"],
        "reuse_value": 120, "material_value": 35, "repair_cost": 60,
        "repairable": True, "safety_critical": False, "ages_out": False,
        "notes": {
            "reusable": "Spin the shaft by hand, then run it at low voltage to confirm it is smooth and quiet.",
            "repairable": "Common fixes: replace worn brushes, re-solder broken leads, or straighten and re-seat the shaft.",
            "recycle": "Motors are rich in copper and steel. Give it to a scrap or e-waste dealer that separates metals.",
            "testing": "Measure winding resistance, spin it by hand for roughness, and run it briefly at low voltage while watching for heat.",
        },
    },
    "sensor": {
        "display": "Sensor module",
        "aliases": ["sensor", "dht11", "dht22", "ultrasonic", "ldr", "pir", "hc sr04"],
        "reuse_value": 80, "material_value": 8, "repair_cost": 40,
        "repairable": True, "safety_critical": False, "ages_out": False,
        "notes": {
            "reusable": "Wire it to a board and compare its readings against a known reference before reusing it.",
            "repairable": "Clean the sensing element, re-solder loose pins, or replace a damaged probe or lens.",
            "recycle": "Sensor modules carry very little material, so bundle it with other small boards for an e-waste drop-off.",
            "testing": "Connect it to a microcontroller and check the output against a reference. Erratic or flat output means it is not worth keeping.",
        },
    },
    "capacitor": {
        "display": "Capacitor",
        "aliases": ["capacitor", "capacitors", "cap", "electrolytic"],
        "reuse_value": 10, "material_value": 2, "repair_cost": 0,
        "repairable": False, "safety_critical": True, "ages_out": True,
        "notes": {
            "reusable": "Confirm its capacitance and leakage with a meter first. Electrolytic capacitors dry out with age.",
            "repairable": "Capacitors are replaced, not repaired. Keep it only if a meter shows it is within tolerance.",
            "recycle": "Include it with other boards for e-waste recycling. Bulging or leaking capacitors should not be reused.",
            "testing": "Measure capacitance and ESR with a meter. Discharge it safely before handling.",
        },
    },
}

DEFAULT = {
    "display": "Electronic component",
    "aliases": [],
    "reuse_value": 50, "material_value": 5, "repair_cost": 20,
    "repairable": False, "safety_critical": False, "ages_out": False,
    "notes": {
        "reusable": "Test it in a simple circuit before reusing it.",
        "repairable": "Look for a loose joint, broken lead or dirty contact, and retest after fixing it.",
        "recycle": "Send it to an authorised e-waste recycler for material recovery.",
        "testing": "Test it with a multimeter or in a simple circuit before deciding.",
    },
}


def _norm(text):
    return " ".join(str(text).lower().replace("_", " ").replace("-", " ").split())


def canonical_name(raw):
    """Map a model class label such as 'Arduino_Uno' to a key in COMPONENTS."""
    norm = _norm(raw)
    if norm in COMPONENTS:
        return norm
    tokens = set(norm.split())
    for key, info in COMPONENTS.items():
        for alias in [key] + info["aliases"]:
            alias = _norm(alias)
            if (" " in alias and alias in norm) or alias in tokens:
                return key
    return norm or "unknown"


def get_component(key):
    info = dict(DEFAULT)
    info.update(COMPONENTS.get(key, {}))
    if key not in COMPONENTS:
        info["display"] = str(key).title() if key and key != "unknown" else DEFAULT["display"]
    return info


def display_name(key):
    return get_component(key)["display"]
