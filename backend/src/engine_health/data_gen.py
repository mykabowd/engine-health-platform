"""Synthetic engine-degradation data generator.

Generates plausible run-to-failure sensor trajectories entirely in-process
with numpy - no download of the real NASA C-MAPSS dataset is required. This
keeps the project 100% self-contained and fast to build/deploy/test, which
matters more here than scientific fidelity (see README for the honest
"what this project does / does not demonstrate" section).

Each simulated engine unit has:
  - a random total lifetime (cycles until failure),
  - a handful of sensors that drift away from a healthy baseline as the
    unit approaches failure (quadratic degradation curve + Gaussian noise),
  - a Remaining Useful Life (RUL) label at every cycle: ``life - cycle``.

The same generator is used to build:
  1. the bulk training set consumed by ``train.py``, and
  2. the small fixed "demo fleet" served by the API (different seed, and the
     demo units are truncated *before* failure so the frontend has something
     interesting - but not already-failed - to display).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from engine_health.config import SENSOR_NAMES

# Per-sensor degradation profile: (baseline, direction, magnitude, noise_std).
# `direction` is +1 (sensor rises as the engine degrades) or -1 (falls).
_SENSOR_PROFILES: dict[str, tuple[float, float, float, float]] = {
    "sensor_temp": (640.0, +1.0, 55.0, 3.0),
    "sensor_pressure": (30.0, -1.0, 6.0, 0.6),
    "sensor_vibration": (0.35, +1.0, 0.9, 0.05),
    "sensor_fuel_flow": (8.0, +1.0, 2.5, 0.25),
}


@dataclass
class EngineTrajectory:
    """Full simulated history of a single engine unit."""

    engine_id: str
    life: int
    cycles: np.ndarray  # shape (n,)
    sensors: np.ndarray  # shape (n, n_sensors)
    rul: np.ndarray  # shape (n,)


def _degrade(
    cycle: np.ndarray,
    life: int,
    profile: tuple[float, float, float, float],
    rng: np.random.Generator,
) -> np.ndarray:
    baseline, direction, magnitude, noise_std = profile
    progress = cycle / life  # 0 -> 1 as the unit approaches failure
    trend = baseline + direction * magnitude * (progress**2)
    noise = rng.normal(0.0, noise_std, size=cycle.shape)
    return trend + noise


def generate_unit(
    engine_id: str,
    rng: np.random.Generator,
    min_life: int = 120,
    max_life: int = 360,
    truncate_before_failure: int = 0,
) -> EngineTrajectory:
    """Simulate one engine unit's full (or truncated) run.

    ``truncate_before_failure`` lets callers stop the trajectory a number of
    cycles before actual failure, which is what the "in-service" demo fleet
    needs (we don't want to show already-failed demo units).
    """
    life = int(rng.integers(min_life, max_life + 1))
    n_cycles = max(1, life - truncate_before_failure)
    cycles = np.arange(1, n_cycles + 1)

    sensor_columns = [_degrade(cycles, life, _SENSOR_PROFILES[name], rng) for name in SENSOR_NAMES]
    sensors = np.column_stack(sensor_columns)
    rul = (life - cycles).astype(float)

    return EngineTrajectory(engine_id=engine_id, life=life, cycles=cycles, sensors=sensors, rul=rul)


def generate_training_set(
    n_units: int = 60,
    seed: int = 42,
    min_life: int = 120,
    max_life: int = 360,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a flat (X, y) training set from many run-to-failure units.

    X columns: [cycle, sensor_0, sensor_1, ..., sensor_k]
    y: RUL (float, cycles remaining until failure)
    """
    rng = np.random.default_rng(seed)
    X_rows: list[np.ndarray] = []
    y_rows: list[float] = []

    for i in range(n_units):
        traj = generate_unit(f"train-unit-{i:03d}", rng, min_life=min_life, max_life=max_life)
        cycle_col = traj.cycles.reshape(-1, 1)
        X_unit = np.hstack([cycle_col, traj.sensors])
        X_rows.append(X_unit)
        y_rows.append(traj.rul)

    X = np.vstack(X_rows)
    y = np.concatenate(y_rows)
    return X, y


def healthy_baseline_stats(
    n_units: int = 60, seed: int = 42, early_fraction: float = 0.1
) -> tuple[np.ndarray, np.ndarray]:
    """Mean/std of each sensor during the early ("healthy") portion of life.

    Used at inference time to flag anomalous sensor readings via a simple
    z-score against what a healthy engine normally looks like.
    """
    rng = np.random.default_rng(seed)
    healthy_rows: list[np.ndarray] = []

    for i in range(n_units):
        traj = generate_unit(f"baseline-unit-{i:03d}", rng)
        cutoff = max(1, int(len(traj.cycles) * early_fraction))
        healthy_rows.append(traj.sensors[:cutoff])

    healthy = np.vstack(healthy_rows)
    return healthy.mean(axis=0), healthy.std(axis=0)


def generate_demo_fleet(n_units: int, seed: int) -> list[EngineTrajectory]:
    """Generate the small, fixed fleet of "in-service" units shown by the API.

    Each unit is truncated a random number of cycles before its simulated
    failure point, so it represents an engine currently in operation with an
    unknown-to-the-user (but computable) remaining life.
    """
    rng = np.random.default_rng(seed)
    fleet: list[EngineTrajectory] = []
    for i in range(n_units):
        truncate = int(rng.integers(5, 80))
        traj = generate_unit(f"ENG-{i + 1:03d}", rng, truncate_before_failure=truncate)
        fleet.append(traj)
    return fleet
