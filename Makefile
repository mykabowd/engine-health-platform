.PHONY: backend-install backend-train backend-test backend-lint backend-run \
        frontend-install frontend-build frontend-lint frontend-dev \
        docker-build docker-up docker-down \
        k8s-cluster-create k8s-import-images helm-install helm-uninstall \
        k8s-deploy k8s-verify k8s-destroy

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------

backend-install:
	python3.11 -m venv backend/.venv
	backend/.venv/bin/pip install --upgrade pip
	backend/.venv/bin/pip install -r backend/requirements.txt
	backend/.venv/bin/pip install -e backend
	backend/.venv/bin/pip install pytest ruff

backend-train:
	backend/.venv/bin/python -m engine_health.train

backend-test:
	cd backend && ../backend/.venv/bin/pytest -v

backend-lint:
	cd backend && ../backend/.venv/bin/ruff check src tests

backend-run:
	cd backend && ../backend/.venv/bin/uvicorn engine_health.main:app --reload --port 8000

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint

frontend-dev:
	cd frontend && npm run dev

# ---------------------------------------------------------------------------
# Docker (local dev)
# ---------------------------------------------------------------------------

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v

# ---------------------------------------------------------------------------
# Kubernetes (k3d + Helm) - real local cluster deployment
# ---------------------------------------------------------------------------

k8s-cluster-create:
	k3d cluster create engine-health -p "30080:30080@server:0" --wait

k8s-import-images:
	docker build -t engine-health-api:0.1.0 backend/
	docker build -t engine-health-web:0.1.0 frontend/
	k3d image import engine-health-api:0.1.0 engine-health-web:0.1.0 -c engine-health

helm-install:
	helm install engine-health ./helm/engine-health-platform

helm-uninstall:
	helm uninstall engine-health || true

# Full deploy: create cluster, build+import images, helm install, wait for rollout.
k8s-deploy: k8s-cluster-create k8s-import-images helm-install
	kubectl rollout status deployment/engine-health-api --timeout=90s
	kubectl rollout status deployment/engine-health-web --timeout=90s

# Curl-based smoke test against the NodePort exposed by the chart.
k8s-verify:
	kubectl get pods -o wide
	kubectl get svc
	curl -sf http://localhost:30080/api/health && echo
	curl -sf http://localhost:30080/ -o /dev/null -w "web root: HTTP %{http_code}\n"

k8s-destroy:
	-helm uninstall engine-health
	-k3d cluster delete engine-health
