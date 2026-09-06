"""Pydantic models (request/response contracts) for the Engine Health API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from engine_health.config import SENSOR_NAMES


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool
    sensor_names: list[str]


class SensorReading(BaseModel):
    """A single point-in-time sensor reading for a predict request."""

    cycle: float = Field(..., ge=0, description="Operational cycle count for this reading.")
    sensor_temp: float = Field(..., description="Simulated turbine temperature-like sensor.")
    sensor_pressure: float = Field(..., description="Simulated pressure-like sensor.")
    sensor_vibration: float = Field(..., description="Simulated vibration-like sensor.")
    sensor_fuel_flow: float = Field(..., description="Simulated fuel-flow-like sensor.")

    def to_feature_list(self) -> list[float]:
        return [getattr(self, name) for name in SENSOR_NAMES]


class PredictResponse(BaseModel):
    predicted_rul: float
    is_anomaly: bool
    max_abs_z_score: float
    sensor_z_scores: dict[str, float]


class EngineSummary(BaseModel):
    engine_id: str
    current_cycle: int
    latest_reading: SensorReading
    predicted_rul: float
    is_anomaly: bool


class EnginesListResponse(BaseModel):
    engines: list[EngineSummary]
    count: int


class HistoryPoint(BaseModel):
    cycle: int
    sensor_temp: float
    sensor_pressure: float
    sensor_vibration: float
    sensor_fuel_flow: float
    predicted_rul: float


class HistoryResponse(BaseModel):
    engine_id: str
    points: list[HistoryPoint]
