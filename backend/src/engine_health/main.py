"""FastAPI application entrypoint for the Engine Health Platform API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from engine_health import demo_data
from engine_health.config import ALLOWED_ORIGINS, MODEL_PATH, SENSOR_NAMES
from engine_health.model import get_artifact, predict_rul
from engine_health.schemas import (
    EnginesListResponse,
    HealthResponse,
    HistoryResponse,
    PredictResponse,
    SensorReading,
)


@asynccontextmanager
async def _lifespan(_: FastAPI):
    # Loads (or trains, as a fallback) the model artifact once at startup so
    # the first real request isn't slowed down by a cold load/train.
    get_artifact()
    yield


app = FastAPI(
    title="Engine Health Platform API",
    description=(
        "Predictive-maintenance demo API: predicts Remaining Useful Life "
        "(RUL) for aircraft engine units from sensor readings, trained on a "
        "synthetic degradation dataset generated locally."
    ),
    version="0.1.0",
    lifespan=_lifespan,
)

# CORS is enabled here (rather than relying solely on the nginx reverse proxy)
# so the API remains directly usable during local frontend development
# (`npm run dev` against a backend running on a different port) - see the
# README section "Choix CORS vs reverse proxy" for the full rationale. In the
# Kubernetes/Docker deployment, nginx *also* reverse-proxies `/api/*` to this
# service, so the frontend never actually needs CORS in that path; this
# middleware is what makes local dev (Vite dev server on :5173, API on :8000)
# work without a proxy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    model_loaded = MODEL_PATH.exists()
    return HealthResponse(status="ok", model_loaded=model_loaded, sensor_names=SENSOR_NAMES)


@app.get("/engines", response_model=EnginesListResponse)
def list_engines() -> EnginesListResponse:
    summaries = demo_data.list_engine_summaries()
    return EnginesListResponse(engines=summaries, count=len(summaries))


@app.get("/engines/{engine_id}/history", response_model=HistoryResponse)
def engine_history(engine_id: str) -> HistoryResponse:
    points = demo_data.get_engine_history(engine_id)
    if points is None:
        raise HTTPException(status_code=404, detail=f"Unknown engine_id '{engine_id}'")
    return HistoryResponse(engine_id=engine_id, points=points)


@app.post("/predict", response_model=PredictResponse)
def predict(reading: SensorReading) -> PredictResponse:
    result = predict_rul(reading.cycle, reading.to_feature_list())
    return PredictResponse(**result)
