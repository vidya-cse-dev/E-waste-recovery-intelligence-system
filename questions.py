"""Component-specific follow-up questions.

Each option carries a `signal` the decision system understands:
  good / partial / bad / unknown / hazard
Questions have a `kind`:
  function  - does it work?            physical - visible or physical condition
  history   - how it was used          safety   - hazard warning signs
  age       - how old (uses age_factor and old instead of a signal)
Optional option fields: repairable (points to a fixable fault), note (plain-language
reason shown in the result).
"""


def _opt(value, label, signal="unknown", **extra):
    return {"value": value, "label": label, "signal": signal, **extra}


QUESTIONS = {
    "battery": [
        {"id": "bat_swelling", "kind": "safety",
         "text": "Is the battery swollen, hot, or leaking fluid?",
         "options": [
             _opt("no", "No, it looks and feels normal", "good"),
             _opt("yes", "Yes, one or more of these", "hazard",
                  note="You reported swelling, heat or leakage, which makes a battery unsafe to reuse."),
             _opt("unsure", "Not sure", "unknown"),
         ]},
        {"id": "bat_charge", "kind": "function",
         "text": "When you last tested it, did it charge and hold power?",
         "options": [
             _opt("works", "Yes, it works normally", "good"),
             _opt("weak", "It works but drains quickly", "partial", note="You said it drains quickly."),
             _opt("dead", "No, it is dead or will not charge", "bad", note="You said it will not charge or hold power."),
             _opt("never", "I have not tested it", "unknown"),
         ]},
        {"id": "bat_age", "kind": "age",
         "text": "How long was it in use?",
         "options": [
             _opt("lt1", "Under a year", age_factor=1.0),
             _opt("1to3", "1 to 3 years", age_factor=0.8),
             _opt("gt3", "More than 3 years", age_factor=0.55, old=True, note="It is more than 3 years old."),
             _opt("dk", "I don't know", age_factor=0.7),
         ]},
    ],
    "arduino": [
        {"id": "ard_power", "kind": "function",
         "text": "Does the power LED light up when you connect it over USB?",
         "options": [
             _opt("yes", "Yes, it lights up", "good"),
             _opt("no", "No, it stays dark", "bad", note="You said the board does not power on."),
             _opt("never", "I have never tried", "unknown"),
         ]},
        {"id": "ard_upload", "kind": "function",
         "text": "Can you upload a sketch to it?",
         "options": [
             _opt("yes", "Yes, uploads and runs fine", "good"),
             _opt("fails", "Upload fails or it behaves erratically", "partial", note="You said uploads fail or it behaves erratically."),
             _opt("never", "I have never tried", "unknown"),
         ]},
        {"id": "ard_pins", "kind": "physical",
         "text": "Any burnt pins, damaged headers or a broken USB port?",
         "options": [
             _opt("no", "No damage", "good"),
             _opt("yes", "Yes, there is damage", "partial", repairable=True, note="You reported damaged pins, headers or USB port, which are usually fixable."),
             _opt("unsure", "Not sure", "unknown"),
         ]},
    ],
    "motor": [
        {"id": "mot_spin", "kind": "function",
         "text": "Does it spin freely by hand and when powered?",
         "options": [
             _opt("smooth", "Yes, smooth and quiet", "good"),
             _opt("rough", "It spins but is noisy, weak or gets hot", "partial", note="You said it runs rough, weak or hot."),
             _opt("jammed", "No, it is jammed or does not spin", "bad", note="You said it does not spin."),
             _opt("never", "I have not tested it", "unknown"),
         ]},
        {"id": "mot_burnt", "kind": "physical",
         "text": "Was there a burnt smell or overheating while it was in use?",
         "options": [
             _opt("no", "No", "good"),
             _opt("yes", "Yes", "partial", note="You reported a burnt smell or overheating, which points to winding damage."),
             _opt("unsure", "Not sure", "unknown"),
         ]},
        {"id": "mot_shaft", "kind": "physical",
         "text": "Is the shaft bent, or are the terminals or wires broken?",
         "options": [
             _opt("no", "No", "good"),
             _opt("yes", "Yes", "partial", repairable=True, note="You reported a bent shaft or broken terminals, which can often be fixed."),
             _opt("unsure", "Not sure", "unknown"),
         ]},
    ],
    "sensor": [
        {"id": "sen_output", "kind": "function",
         "text": "When connected, does it give a sensible reading?",
         "options": [
             _opt("yes", "Yes, readings look right", "good"),
             _opt("erratic", "Readings are erratic or wrong", "partial", note="You said the readings are erratic or wrong."),
             _opt("none", "No output at all", "bad", note="You said it gives no output."),
             _opt("never", "I have not tested it", "unknown"),
         ]},
        {"id": "sen_element", "kind": "physical",
         "text": "Is the sensing part (probe, lens or membrane) intact and clean?",
         "options": [
             _opt("yes", "Yes", "good"),
             _opt("damaged", "It is damaged or dirty", "partial", repairable=True, note="You said the sensing part is damaged or dirty."),
             _opt("unsure", "Not sure", "unknown"),
         ]},
        {"id": "sen_env", "kind": "history",
         "text": "Was it used somewhere wet, dusty or corrosive?",
         "options": [
             _opt("no", "No", "good"),
             _opt("yes", "Yes", "partial", note="You said it was used in a wet, dusty or corrosive place."),
             _opt("unsure", "Not sure", "unknown"),
         ]},
    ],
    "capacitor": [
        {"id": "cap_bulge", "kind": "safety",
         "text": "Is the top bulging or vented, or is there leaked fluid?",
         "options": [
             _opt("no", "No", "good"),
             _opt("yes", "Yes", "hazard", note="You reported bulging or leakage, which means the capacitor has failed."),
             _opt("unsure", "Not sure", "unknown"),
         ]},
        {"id": "cap_marking", "kind": "physical",
         "text": "Can you still read the rating (µF and voltage) on the body?",
         "options": [
             _opt("yes", "Yes, it is readable", "good"),
             _opt("no", "No, it is worn or unreadable", "partial", note="The rating is unreadable, so it cannot be matched to a circuit without a meter."),
         ]},
        {"id": "cap_measured", "kind": "function",
         "text": "Have you measured it with a capacitance meter?",
         "options": [
             _opt("ok", "Yes, it reads close to its rating", "good"),
             _opt("off", "Yes, but the reading is far off", "bad", note="You said its measured value is far from its rating."),
             _opt("no", "No, not measured", "unknown"),
         ]},
        {"id": "cap_age", "kind": "age",
         "text": "How old is the board or device it came from?",
         "options": [
             _opt("lt5", "Under 5 years", age_factor=1.0),
             _opt("5to10", "5 to 10 years", age_factor=0.7),
             _opt("gt10", "More than 10 years", age_factor=0.4, old=True, note="It is more than 10 years old."),
             _opt("dk", "I don't know", age_factor=0.7),
         ]},
    ],
}

DEFAULT_QUESTIONS = [
    {"id": "gen_works", "kind": "function",
     "text": "Did this part work the last time it was used?",
     "options": [
         _opt("yes", "Yes", "good"),
         _opt("partly", "Partly", "partial", note="You said it only partly worked."),
         _opt("no", "No", "bad", note="You said it did not work."),
         _opt("unknown", "I don't know", "unknown"),
     ]},
    {"id": "gen_damage", "kind": "physical",
     "text": "Any burn marks, burnt smell or physical damage you can see or feel?",
     "options": [
         _opt("no", "No", "good"),
         _opt("yes", "Yes", "partial", note="You reported burn marks, smell or physical damage."),
         _opt("unsure", "Not sure", "unknown"),
     ]},
    {"id": "gen_hazard", "kind": "safety",
     "text": "Is it leaking, swollen or hot?",
     "options": [
         _opt("no", "No", "good"),
         _opt("yes", "Yes", "hazard", note="You reported leaking, swelling or heat, which is a safety concern."),
     ]},
]


def get_questions(component):
    return QUESTIONS.get(component, DEFAULT_QUESTIONS)


def public_questions(component):
    """Questions as sent to the browser: no scoring fields."""
    return [
        {"id": q["id"], "text": q["text"],
         "options": [{"value": o["value"], "label": o["label"]} for o in q["options"]]}
        for q in get_questions(component)
    ]
