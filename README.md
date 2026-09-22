# AI-Based Electronic Component Recovery & Circular Value Intelligence

A system that helps people decide what to do with old electronic components. A user uploads a photo; the
system identifies the component, checks it for visible damage, asks a few component-specific questions when
the photo is not enough, and recommends whether the part is **potentially reusable**, **potentially
repairable**, suited to **recycling / material recovery**, or **needs further testing**, with an estimated
recovery value. A web app shows each result and Power BI shows dashboards across all results.

## How it works

```
photo --> YOLO detector --> Condition AI --> enough information? --no--> follow-up questions
          (what is it?)     (visible damage)          |yes                    |
                                                      v                       v
                                              Decision system  <---------------
                                              (4 outcomes + reasons)
                                                      |
                                                      v
                                        Value estimate (Rs low - high)
                                                      |
                                       SQLite log --> Web app + Power BI
```

| Stage | File | What it does |
| --- | --- | --- |
| 1. Identify | `detector.py` | Runs your trained YOLO weights and maps class names to component types |
| 2. Inspect | `condition.py` | Finds cracks, burns, corrosion, leakage, broken parts; returns severity and confidence |
| 3. Ask | `questions.py`, `pipeline.py` | Component-specific questions, asked only when the photo is not enough |
| 4. Decide | `decision.py` | Rule-based recommendation with plain-language reasons and a certainty score |
| 5. Value | `value.py`, `components.py` | Indicative recovery value range in rupees |
| 6. Show | `app.py`, `templates/`, `static/` | Flask web app and built-in dashboard |
| 7. Analyse | `powerbi/` | Power BI guide, DAX measures and sample data |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                      # open http://127.0.0.1:5000
```

The console prints which mode each model is in, for example `Detector: demo | Condition AI: heuristic`.

## Plug in your trained models

1. **Component detector.** Copy your YOLO weights to `models/component_detector.pt`
   (or set `EWASTE_DETECTOR_WEIGHTS` to their path). The app switches from demo mode to real detection
   automatically. Class names such as `Arduino_Uno` or `dc motor` are matched to component types by
   `components.canonical_name()`.
2. **Condition AI.** Two options:
   - Train one: put labelled crops in `condition_data/train/<class>/` and `condition_data/val/<class>/`, then run
     `python train/train_condition.py --data condition_data`. It saves `models/condition_model.pt`.
   - Or copy any Ultralytics classification or detection weights to `models/condition_model.pt`.
   Class names are mapped to damage types (crack, burn, corrosion, leakage, broken, good) by
   `condition.map_class()`, so folder names like `burnt`, `cracked`, `corroded`, `leaking`, `no_damage` work.
   With no model file, an OpenCV colour-and-edge check is used instead.
3. **A component your model knows but the app does not.** Add one entry to `COMPONENTS` in `components.py`
   (display name, aliases, prices, whether it is repairable and safety-critical, advice text). Optionally add its
   questions in `questions.py`; otherwise generic questions are used.

## The decision rules

Visible damage is banded from the condition severity (none below 0.2, minor below 0.5, moderate below 0.75,
severe above). The user's answers give a function signal (works / partial / fails / unknown) and a hazard flag.

| Situation | Outcome |
| --- | --- |
| Any hazard sign (swelling, bulging, heat, leakage) | Recycle / material recovery |
| Severe damage, does not work or unknown | Recycle / material recovery |
| Severe damage but the user says it works | Needs further testing (image and answer disagree) |
| Moderate damage, works or unknown | Needs further testing |
| Moderate damage, faulty | Repairable if this type of part is repairable, otherwise recycle |
| Minor or no damage, works | Potentially reusable |
| Minor or no damage, partly works | Repairable, or needs testing if the part is not normally repaired |
| Minor or no damage, does not work | Repairable, or recycle if the part is not normally repaired |
| Nothing known, clean photo, safe part type | Potentially reusable |
| Nothing known, but battery or capacitor | Needs further testing (faults are internal) |

Extra guard rails only ever make the outcome more cautious: an old battery or capacitor is downgraded from
reusable to testing, and low detection confidence with no answers blocks reuse and repair.

Certainty combines the detector and condition confidence, rises as more questions are answered, and is capped
at 60% whenever the outcome is "needs further testing".

## The value estimate

`reuse_value` and `material_value` per component are in `components.py`. Reusable parts are valued at the reuse
price reduced by damage and age; repairable parts at 70% of the reuse price minus a repair cost; recycled parts at
scrap value (less for hazardous parts); parts needing testing get a range from scrap value to the reuse value.
These prices are **assumptions**. Replace them with figures from local second-hand and scrap markets and cite the
source in your report.

## When the app asks questions

Questions appear when detection confidence is low, when condition confidence is low (blurry or small photo), when
damage is moderate, or when the part is a battery or capacitor with a clean-looking photo. Even when the result is
decided straight away, **Answer a few questions to refine this** lets the user add information.

## Web app and API

| Route | Purpose |
| --- | --- |
| `GET /` | Upload page and result |
| `GET /dashboard` | Built-in dashboard (Chart.js) |
| `POST /api/analyze` | Multipart `image` (+ optional `component`) returns detection, condition, and questions or a decision |
| `POST /api/decide` | JSON `{id, answers}` returns the decision and value |
| `GET /api/stats`, `/api/records` | Aggregates and latest records |
| `GET /export/records.csv` | CSV for Power BI |

## Power BI

See `powerbi/POWERBI_GUIDE.md` for the data steps, DAX measures and page layouts.
`python seed_data.py` writes `powerbi/ewaste_sample_records.csv` (150 **synthetic** rows produced by the real
decision code) so you can build the dashboard before you have real results. `python seed_data.py --insert` also
loads them into the app dashboard, flagged as samples. Do not present them as real results.

## Tests

```bash
python -m pytest tests -q
```

30 tests cover the decision rules, the value estimator, the model-output parsing (with fake Ultralytics results),
and the full web API using synthetic images.

## Limitations to state in your report

- The OpenCV fallback judges colour and edges only. It can confuse gold contacts, green PCBs and black casings with
  damage, and it cannot see broken or missing parts. A trained Condition AI is more reliable.
- A photo cannot show internal faults, which is why batteries and capacitors always trigger questions.
- Decision rules are expert-defined, not learned, so they are explainable but reflect design choices.
- Value figures are indicative and depend on the price assumptions in `components.py`.
- The system supports the decision; hazardous parts (swollen batteries, bulging capacitors) should be handled by
  an authorised e-waste recycler.

## Likely viva questions

**Why rules for the decision instead of another model?** There is no labelled dataset of "what should be done with
this part", every recommendation must be explainable and safe, and rules let the system default to "needs further
testing" instead of guessing.

**Why ask questions at all?** A photo shows the outside only. Whether a battery holds charge or a motor spins is
invisible, so the system asks only when the image is insufficient.

**How do you handle uncertainty?** Detector and condition confidences feed a certainty score, low confidence
triggers questions, and conflicting evidence leads to "needs further testing".

**How is the value estimated?** Indicative reuse and scrap prices per component, adjusted for damage, age and the
recommended route, shown as a range.

**What is the circular-economy benefit?** Parts are routed to reuse or repair before recycling, and hazardous parts
are steered to proper collection.
