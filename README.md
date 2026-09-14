🇫🇷 [Version française](README.fr.md)

# engine-health-platform

**Full-stack** "engine health" service: a Python API (FastAPI) predicts
the remaining useful life (**RUL**, *Remaining Useful Life*) of aircraft
engine units from sensor readings, and a React frontend displays the demo
fleet, the current prediction, and cycle history. The whole thing is
containerized, and has been **actually deployed and verified** on a local
Kubernetes cluster (`k3d` + `Helm`) — not just written.

Thematic continuity with
[`ml-critical-systems-lab`](../ml-critical-systems-lab) (predictive
maintenance on NASA C-MAPSS data): same domain (aircraft engine
degradation), but here exposed as an actual **service** (API + frontend +
Docker + Kubernetes), rather than just an offline study
(notebooks/report).

## Why this project

This project was born from wanting to design a complete application,
from the user interface all the way down to its deployment, while
putting into practice a modern architecture and several complementary
technologies (Python API, React frontend, containerization, real
Kubernetes deployment, CI/CD):

| Technical aspect | Where it's implemented |
|---|---|
| Building backend services, APIs, microservices in Python | `backend/` — full FastAPI application (4 endpoints, Pydantic, tests) |
| Lightweight interfaces, web prototypes, demos | `frontend/` — React/Vite SPA with a chart |
| Integrating frontend, backend, AI services (ML model), DB/API | Frontend → nginx (reverse proxy) → FastAPI API → scikit-learn model |
| Creating/maintaining/optimizing Docker images | `backend/Dockerfile`, `frontend/Dockerfile` (multi-stage) |
| Developing/maintaining Helm charts for Kubernetes | `helm/engine-health-platform/` — **actually installed** via `helm install` on a k3d cluster |
| Automating deployments/configuration/environments | `Makefile` (`k8s-deploy`, `k8s-verify`, `k8s-destroy` targets), `.gitlab-ci.yml` |
| Diagnosing/fixing Kubernetes issues | `docs/troubleshooting.md` — a real `NodePort` connectivity issue encountered and fixed (see below) |
| Modern frontend frameworks (React, Angular...) | React 19 + Vite + recharts |
| CI/CD tooling (GitLab CI) | `.gitlab-ci.yml` — 4 stages, syntactically valid (not run on a real runner, see CI/CD section) |

It complements the two other projects in my portfolio by taking a
different approach and offering a more complete, hands-on technical
experience — where [`genai-mcp-assistant`](../genai-mcp-assistant) explores
RAG, agents, and an MCP server, and
[`ml-critical-systems-lab`](../ml-critical-systems-lab) in-depth classic ML
with a technical report. Here, the ML model is deliberately simple (a
`RandomForestRegressor` on synthetic data) — the goal of *this* project is
full-stack + Kubernetes integration, not ML research.

## Tech stack

- **Backend**: Python 3.11, FastAPI, Pydantic, scikit-learn, numpy, joblib
- **Frontend**: React 19, Vite, recharts
- **Containerization**: Docker (multi-stage images), docker-compose
- **Kubernetes**: Helm (full chart), deployed and verified on `k3d`
- **CI/CD**: GitLab CI (`.gitlab-ci.yml` — lint / test / build / deploy)
- **Tests**: pytest + `fastapi.testclient.TestClient` (11 tests)

## Architecture

```
┌──────────────────┐   GET /               ┌──────────────────────┐
│  Browser          │   GET/POST /api/*     │  nginx (web pod)      │
│  (React SPA)       │ ───────────────────► │  - serves dist/ (React)│
└──────────────────┘                        │  - proxies /api/* → api│
                                             └───────────┬───────────┘
                                                         │ HTTP (in-cluster)
                                                         ▼
                                             ┌──────────────────────┐
                                             │  FastAPI (api pod)     │
                                             │  /health                │
                                             │  /engines                │
                                             │  /engines/{id}/history    │
                                             │  /predict                  │
                                             └───────────┬─────────────────┘
                                                         │
                                                         ▼
                                             ┌──────────────────────┐
                                             │  model.joblib           │
                                             │  RandomForestRegressor  │
                                             │  (synthetic data,       │
                                             │   see train.py)          │
                                             └──────────────────────┘
```

Locally (docker-compose) and on Kubernetes (Helm), the topology is
identical: two components (`api`, `web`), the frontend always calls
`/api/*` same-origin, and nginx routes to the `api` service — see the
**CORS vs reverse proxy choice** section below for details.

### CORS vs reverse proxy choice

The frontend always calls `/api/*` **same-origin** (no hardcoded absolute
URL):

- In **production / Docker / Kubernetes**, nginx reverse-proxies `/api/*`
  to the backend service (`frontend/nginx.conf` locally,
  `helm/.../templates/web-nginx-configmap.yaml` on Kubernetes with the
  actual Service name). The browser therefore **never** makes a
  cross-origin request on this path — no client-side CORS configuration
  to trust.
- In **local development** (`npm run dev`, Vite on `:5173`, API on
  `:8000`, no proxy), the frontend calls
  `http://localhost:8000` directly (via `VITE_API_URL`, see
  `frontend/.env.development`), and that's where FastAPI's CORS
  middleware (`backend/src/engine_health/main.py`) comes into play, so
  that `npm run dev` works without running nginx.

Both mechanisms coexist, but for different, complementary reasons — the
proxy is the "robust" solution used for any real deployment; CORS is
purely a local development convenience.

## Quickstart (local, without Kubernetes)

### Backend only (venv)

```bash
make backend-install   # creates backend/.venv, installs dependencies
make backend-train      # (re)trains the model -> backend/src/engine_health/artifacts/model.joblib
make backend-test        # pytest -v (11 tests)
make backend-run          # uvicorn --reload on :8000
```

The model is already committed to the repo (`model.joblib`, ~76 KB):
`make backend-train` is only needed if you want to regenerate it.

### Frontend only (Vite dev server)

```bash
make frontend-install
make frontend-dev   # http://localhost:5173, calls http://localhost:8000 (VITE_API_URL)
```

### Both together via Docker Compose (recommended)

```bash
make docker-up
# equivalent to: docker compose up --build
```

Then:

```bash
curl http://localhost:8000/health          # direct API
curl http://localhost:8080/api/engines      # via nginx (frontend)
open http://localhost:8080                   # React SPA
```

Shutdown: `make docker-down` (= `docker compose down -v`).

**Actually verified** on 2026-09-06: `docker compose build` (2 images
built), `docker compose up -d` (2 `healthy` containers), then:
- `curl http://localhost:8000/health` → `{"status":"ok","model_loaded":true,...}`
- `curl http://localhost:8080/api/engines` → list of 6 engine units with predicted RUL
- `curl -X POST http://localhost:8080/api/predict -d '{...}'` → prediction + anomaly flag
- `curl http://localhost:8080/` → `HTTP 200` (React page served by nginx)

## Quickstart (local Kubernetes, k3d + Helm)

Prerequisites installed for this project: `brew install k3d kubectl helm`
(Docker already available via Colima).

```bash
make k8s-deploy   # creates the k3d cluster, builds+imports images, helm install, waits for rollout
make k8s-verify    # kubectl get pods/svc + curl on NodePort 30080
make k8s-destroy    # helm uninstall + k3d cluster delete (full cleanup)
```

Or step by step:

```bash
k3d cluster create engine-health -p "30080:30080@server:0" --wait

docker build -t engine-health-api:0.1.0 backend/
docker build -t engine-health-web:0.1.0 frontend/
k3d image import engine-health-api:0.1.0 engine-health-web:0.1.0 -c engine-health

helm install engine-health ./helm/engine-health-platform

kubectl rollout status deployment/engine-health-api --timeout=90s
kubectl rollout status deployment/engine-health-web --timeout=90s

kubectl get pods -o wide
curl http://localhost:30080/api/health
curl http://localhost:30080/
```

**This deployment was actually executed and verified** on 2026-09-06
(cluster destroyed afterward to leave nothing running). Full output of
`kubectl get pods`, `kubectl get svc`, `helm install`, and verification
`curl` commands: see
**[`docs/k8s-verification.md`](docs/k8s-verification.md)**.

A real connectivity issue was encountered and fixed during this
deployment (the `NodePort` was not reachable from the macOS host without
an explicit port mapping at k3d cluster creation): full diagnostic in
**[`docs/troubleshooting.md`](docs/troubleshooting.md)**.

### Why NodePort rather than an Ingress

A `NodePort`-type `Service` was chosen over an `Ingress` resource: this
gives a directly `curl`-able external access point without installing and
configuring an additional Ingress controller (nginx-ingress, Traefik...)
on the local cluster — an extra dependency to operate that isn't needed
to demonstrate the targeted skills (writing and actually deploying a Helm
chart). See `helm/engine-health-platform/values.yaml`.

## Project structure

```
engine-health-platform/
├── backend/
│   ├── src/engine_health/
│   │   ├── config.py         # centralized configuration (env vars)
│   │   ├── data_gen.py         # synthetic degradation data generator
│   │   ├── train.py             # trains the RandomForestRegressor -> model.joblib
│   │   ├── model.py              # model loading + prediction + anomaly detection
│   │   ├── demo_data.py           # in-memory demo fleet (fixed seed)
│   │   ├── schemas.py              # Pydantic models (requests/responses)
│   │   ├── main.py                  # FastAPI application (4 endpoints)
│   │   └── artifacts/model.joblib    # trained, committed model (~76 KB)
│   ├── tests/test_api.py               # 11 pytest tests (TestClient)
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # single page: selector, RUL/anomaly cards, chart
│   │   ├── api.js               # fetch wrapper (configurable VITE_API_URL)
│   │   └── ...
│   ├── nginx.conf                # reverse-proxy /api/* (default config, docker-compose)
│   └── Dockerfile                 # multi-stage: node (build) -> nginx (serve)
├── helm/engine-health-platform/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/                  # Deployment+Service (api, web), nginx ConfigMap
├── docs/
│   ├── k8s-verification.md          # proof of the real k3d/Helm deployment
│   └── troubleshooting.md            # issues encountered and fixed
├── docker-compose.yml
├── .gitlab-ci.yml                     # lint/test/build/deploy pipeline
├── Makefile
└── .gitignore
```

## CI/CD — GitLab CI

A complete `.gitlab-ci.yml` is provided with 4 stages:

1. **lint**: `ruff` on the backend, `npm run lint` (oxlint) on the frontend
2. **test**: `pytest` on the backend (with a JUnit report artifact)
3. **build**: `docker build` of the 2 images, pushed to
   `$CI_REGISTRY_IMAGE` (GitLab's built-in container registry)
4. **deploy**: `when: manual` stage that **documents in comments** how a
   `helm upgrade --install` would be run against a real cluster

**Honesty note**: this pipeline **has not been run on a real GitLab
runner** (no GitLab account/project connected in this local portfolio
project context). It was verified as follows:
- YAML is syntactically valid (parsed with `PyYAML`)
- Each individual command (`ruff check`, `pytest`, `npm run lint`,
  `docker build`) was **actually run locally** successfully (see
  previous sections) — the pipeline assembles these same commands using
  standard GitLab CI syntax, but end-to-end execution on a runner has not
  been tested.

## What this project demonstrates (and what it does not)

**Demonstrates**:
- Building a Python API (FastAPI) with multiple endpoints, Pydantic
  validation, automated tests (pytest, 11 passing tests)
- Building a React frontend (Vite) consuming this API, a data chart
  (recharts), configuration via environment variables
- Multi-service Docker containerization (lightweight Python image,
  multi-stage node→nginx build), orchestrated via docker-compose
- Writing **and actually deploying, with verification,** a Helm chart on
  a local Kubernetes cluster (k3d): `helm install`, `Running`/`Ready`
  pods, `NodePort` service successfully queried via `curl`
- Diagnosing and fixing a real Kubernetes connectivity issue
  (NodePort/k3d), documented with the exact cause and fix
- Structuring a GitLab CI/CD pipeline (lint/test/build/deploy stages)
  following standard practices

**Does NOT demonstrate** (should not be oversold on a résumé):
- Actual execution of the CI/CD pipeline on a connected GitLab runner (no
  GitLab account used here — see CI/CD section above)
- Ingress controller, TLS, or any "production hardening" (NodePort is a
  deliberately simple solution for a local demo cluster)
- Autoscaling (HPA), real multi-node/multi-replica high availability
  (the chart supports `replicaCount` but has only been tested with 1
  replica per component on a single-node cluster)
- Application-level authentication/authorization (no endpoint is
  protected — this is not a production system, but a demo)
- A sophisticated ML model or one trained on real NASA C-MAPSS data (see
  `ml-critical-systems-lab` for that aspect): here, 100% synthetic data
  generated by `numpy`, a deliberately simple `RandomForestRegressor`
  model — the goal is full-stack integration, not model performance

## Known limitations / possible improvements

- No real database: the demo "fleet" is generated in memory at process
  startup (fixed seed), not persisted.
- The model is not automatically retrained in CI (no ML/MLOps pipeline)
  — `model.joblib` is a static, committed artifact.
- The frontend chart only shows the already-known history of each demo
  unit; there's no "live" simulation of new cycles.
- Only one model type tested (RandomForestRegressor); no algorithm
  comparison (that's not the goal of this project — see
  `ml-critical-systems-lab` for that kind of work).
