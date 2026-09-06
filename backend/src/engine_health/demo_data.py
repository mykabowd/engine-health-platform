"""In-memory "demo fleet" of engine units served by GET /engines and
GET /engines/{id}/history.

Generated once (deterministically, fixed seed) at first access and cached
for the lifetime of the process - this is a portfolio/demo API, not a
system of record, so there is no database involved (see README).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from engine_health.config import DEMO_FLEET_SEED, DEMO_FLEET_SIZE, SENSOR_NAMES
from engine_health.data_gen import EngineTrajectory, generate_demo_fleet
from engine_health.model import get_artifact
from engine_health.schemas import EngineSummary, HistoryPoint, SensorReading


@lru_cache(maxsize=1)
def _fleet() -> dict[str, EngineTrajectory]:
    trajectories = generate_demo_fleet(n_units=DEMO_FLEET_SIZE, seed=DEMO_FLEET_SEED)
    return {t.engine_id: t for t in trajectories}


def list_engine_ids() -> list[str]:
    return list(_fleet().keys())


def _predicted_rul_batch(cycles: np.ndarray, sensors: np.ndarray) -> np.ndarray:
    artifact = get_artifact()
    model = artifact["model"]
    features = np.column_stack([cycles, sensors])
    return model.predict(features)


def get_engine_summary(engine_id: str) -> EngineSummary | None:
    traj = _fleet().get(engine_id)
    if traj is None:
        return None

    last_cycle = traj.cycles[-1]
    last_sensors = traj.sensors[-1]

    reading = SensorReading(
        cycle=float(last_cycle),
        **{name: float(value) for name, value in zip(SENSOR_NAMES, last_sensors)},
    )

    from engine_health.model import predict_rul  # local import: avoid a cycle at module load

    prediction = predict_rul(float(last_cycle), reading.to_feature_list())

    return EngineSummary(
        engine_id=engine_id,
        current_cycle=int(last_cycle),
        latest_reading=reading,
        predicted_rul=prediction["predicted_rul"],
        is_anomaly=prediction["is_anomaly"],
    )


def list_engine_summaries() -> list[EngineSummary]:
    summaries = [get_engine_summary(engine_id) for engine_id in list_engine_ids()]
    return [s for s in summaries if s is not None]


def get_engine_history(engine_id: str) -> list[HistoryPoint] | None:
    traj = _fleet().get(engine_id)
    if traj is None:
        return None

    predicted_ruls = _predicted_rul_batch(traj.cycles, traj.sensors)

    points = []
    for i, cycle in enumerate(traj.cycles):
        sensors = traj.sensors[i]
        points.append(
            HistoryPoint(
                cycle=int(cycle),
                sensor_temp=float(sensors[0]),
                sensor_pressure=float(sensors[1]),
                sensor_vibration=float(sensors[2]),
                sensor_fuel_flow=float(sensors[3]),
                predicted_rul=round(float(predicted_ruls[i]), 2),
            )
        )
    return points
