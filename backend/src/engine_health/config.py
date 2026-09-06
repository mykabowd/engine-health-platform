"""Centralized configuration (environment-variable driven, with sane defaults)."""

from __future__ import annotations

import os
from pathlib import Path

# Directory containing this file -> used to resolve the default model path
# relative to the package, regardless of the current working directory.
_PACKAGE_DIR = Path(__file__).resolve().parent

# Sensors simulated for every engine unit. Loosely inspired by the kind of
# multivariate sensor streams found in the NASA C-MAPSS dataset (temperature,
# pressure, vibration, fuel-flow-like signals), but entirely synthetic here.
SENSOR_NAMES: list[str] = ["sensor_temp", "sensor_pressure", "sensor_vibration", "sensor_fuel_flow"]

# Where the trained model artifact lives. Overridable via env var so the
# same image can be pointed at a different artifact without a rebuild.
_DEFAULT_MODEL_PATH = str(_PACKAGE_DIR / "artifacts" / "model.joblib")
MODEL_PATH = Path(os.environ.get("ENGINE_HEALTH_MODEL_PATH", _DEFAULT_MODEL_PATH))

# Anomaly detection thresholds (kept intentionally simple - see README).
Z_SCORE_ANOMALY_THRESHOLD = float(os.environ.get("ENGINE_HEALTH_Z_THRESHOLD", "3.0"))
RUL_ANOMALY_THRESHOLD = float(os.environ.get("ENGINE_HEALTH_RUL_THRESHOLD", "15.0"))

# Random seed used to generate the fixed "demo fleet" shown by GET /engines.
# Kept separate from the training-data seed so the demo fleet is stable
# across retrainings of the model.
DEMO_FLEET_SEED = int(os.environ.get("ENGINE_HEALTH_DEMO_SEED", "2024"))
DEMO_FLEET_SIZE = int(os.environ.get("ENGINE_HEALTH_DEMO_FLEET_SIZE", "6"))

# CORS: allow the Vite dev server and any origin in a simple demo deployment.
# See README "Choix CORS vs reverse proxy" for the rationale.
ALLOWED_ORIGINS = os.environ.get("ENGINE_HEALTH_ALLOWED_ORIGINS", "*").split(",")
