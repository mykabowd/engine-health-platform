"""Loads the trained model artifact and exposes a simple prediction API."""

from __future__ import annotations

import threading
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from engine_health.config import MODEL_PATH, RUL_ANOMALY_THRESHOLD, Z_SCORE_ANOMALY_THRESHOLD
from engine_health.train import train_and_save

_lock = threading.Lock()


class ModelNotAvailableError(RuntimeError):
    """Raised when the model artifact is missing and could not be trained on the fly."""


@lru_cache(maxsize=1)
def get_artifact(model_path: Path = MODEL_PATH) -> dict:
    """Load the model artifact, training it on the fly as a fallback.

    In normal operation the artifact is committed to the repo
    (``src/engine_health/artifacts/model.joblib``), so this is just a
    disk read. The on-the-fly training fallback exists so the service is
    still usable (e.g. in a from-scratch clone without the artifact, or in
    a minimal CI job) without needing a separate step.
    """
    with _lock:
        if not model_path.exists():
            train_and_save(model_path)
        return joblib.load(model_path)


def predict_rul(cycle: float, sensor_values: list[float]) -> dict:
    """Predict RUL for a single reading and flag anomalies.

    Anomaly detection combines two simple, explainable signals:
      1. predicted RUL below ``RUL_ANOMALY_THRESHOLD`` cycles, and/or
      2. any sensor's z-score (vs. the "healthy" baseline captured at
         training time) exceeding ``Z_SCORE_ANOMALY_THRESHOLD``.
    """
    artifact = get_artifact()
    model = artifact["model"]
    baseline_mean: np.ndarray = artifact["baseline_mean"]
    baseline_std: np.ndarray = artifact["baseline_std"]

    features = np.array([[cycle, *sensor_values]], dtype=float)
    predicted_rul = float(model.predict(features)[0])

    sensor_array = np.array(sensor_values, dtype=float)
    # Avoid division by zero for a degenerate/near-constant sensor.
    safe_std = np.where(baseline_std < 1e-6, 1e-6, baseline_std)
    z_scores = (sensor_array - baseline_mean) / safe_std
    max_abs_z = float(np.max(np.abs(z_scores)))

    is_anomaly = bool(
        predicted_rul < RUL_ANOMALY_THRESHOLD or max_abs_z > Z_SCORE_ANOMALY_THRESHOLD
    )

    return {
        "predicted_rul": round(predicted_rul, 2),
        "is_anomaly": is_anomaly,
        "max_abs_z_score": round(max_abs_z, 2),
        "sensor_z_scores": {
            name: round(float(z), 2) for name, z in zip(artifact["sensor_names"], z_scores)
        },
    }
