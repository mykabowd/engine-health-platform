// Small fetch wrapper for the Engine Health backend API.
//
// The base URL is configurable via the Vite env var VITE_API_URL so the
// same build can point at different backends (local dev, docker-compose,
// Kubernetes) without a rebuild in the docker-compose/dev case, and with a
// build-time value baked in for the containerized/K8s case (see
// frontend/Dockerfile and helm values).
const API_URL = import.meta.env.VITE_API_URL || "/api";

async function request(path, options) {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`${options?.method || "GET"} ${path} failed: ${response.status} ${body}`);
  }
  return response.json();
}

export function getEngines() {
  return request("/engines");
}

export function getEngineHistory(engineId) {
  return request(`/engines/${encodeURIComponent(engineId)}/history`);
}

export function predict(reading) {
  return request("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(reading),
  });
}
