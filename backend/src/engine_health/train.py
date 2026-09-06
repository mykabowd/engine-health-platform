"""Train the RUL (Remaining Useful Life) regressor and save the artifact.

Run with:  python -m engine_health.train

This is intentionally lightweight (a small RandomForestRegressor on a
synthetic dataset generated on the fly) so the resulting ``model.joblib``
is a few hundred KB at most and can be committed directly to the repo -
the API does not need network access or a training step at container
start-up.
"""

from __future__ import annotations

import sys
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

from engine_health.config import MODEL_PATH, SENSOR_NAMES
from engine_health.data_gen import generate_training_set, healthy_baseline_stats

TRAIN_SEED = 42


def train_and_save(model_path: Path = MODEL_PATH) -> dict:
    X, y = generate_training_set(n_units=60, seed=TRAIN_SEED)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=TRAIN_SEED
    )

    model = RandomForestRegressor(
        n_estimators=25,
        max_depth=6,
        min_samples_leaf=20,
        random_state=TRAIN_SEED,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, y_pred))

    baseline_mean, baseline_std = healthy_baseline_stats(seed=TRAIN_SEED)

    artifact = {
        "model": model,
        "feature_names": ["cycle", *SENSOR_NAMES],
        "sensor_names": SENSOR_NAMES,
        "baseline_mean": baseline_mean,
        "baseline_std": baseline_std,
        "train_seed": TRAIN_SEED,
        "test_mae": mae,
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path, compress=("gzip", 9))

    return {
        "test_mae": mae,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "model_path": str(model_path),
    }


if __name__ == "__main__":
    result = train_and_save()
    size_kb = Path(result["model_path"]).stat().st_size / 1024
    print(f"Trained RandomForestRegressor on {result['n_train']} samples "
          f"(test={result['n_test']}, test MAE={result['test_mae']:.2f} cycles)")
    print(f"Saved artifact to {result['model_path']} ({size_kb:.1f} KB)")
    sys.exit(0)
