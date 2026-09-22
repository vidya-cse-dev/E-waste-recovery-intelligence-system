"""Central settings. Change paths and thresholds here."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
ANNOTATED_DIR = DATA_DIR / "annotated"
DB_PATH = DATA_DIR / "records.db"
MODELS_DIR = BASE_DIR / "models"

# Drop your trained weights here (or point the environment variables at them).
DETECTOR_WEIGHTS = Path(os.environ.get("EWASTE_DETECTOR_WEIGHTS", MODELS_DIR / "component_detector.pt"))
CONDITION_WEIGHTS = Path(os.environ.get("EWASTE_CONDITION_WEIGHTS", MODELS_DIR / "condition_model.pt"))

DETECTION_CONF = 0.25        # minimum YOLO confidence to keep a detection
LOW_DETECTION_CONF = 0.50    # below this we are unsure which component it is
LOW_CONDITION_CONF = 0.75    # below this the photo is not enough to judge condition

MAX_UPLOAD_MB = 10
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

for _d in (UPLOAD_DIR, ANNOTATED_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
