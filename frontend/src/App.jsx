import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./App.css";
import { getEngineHistory, getEngines, predict } from "./api";

function App() {
  const [engines, setEngines] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [history, setHistory] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [loadingEngines, setLoadingEngines] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState(null);

  // Load the demo fleet once on mount.
  useEffect(() => {
    getEngines()
      .then((data) => {
        setEngines(data.engines);
        if (data.engines.length > 0) {
          setSelectedId(data.engines[0].engine_id);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoadingEngines(false));
  }, []);

  const selectedEngine = useMemo(
    () => engines.find((engine) => engine.engine_id === selectedId) ?? null,
    [engines, selectedId],
  );

  // Load cycle history + a fresh prediction whenever the selection changes.
  useEffect(() => {
    if (!selectedId) return;
    setLoadingHistory(true);
    setError(null);

    getEngineHistory(selectedId)
      .then((data) => setHistory(data.points))
      .catch((err) => setError(err.message))
      .finally(() => setLoadingHistory(false));
  }, [selectedId]);

  // Re-run /predict on the engine's latest reading (rather than just trusting
  // the value from /engines) to demonstrate the POST /predict contract too.
  useEffect(() => {
    if (!selectedEngine) return;
    predict(selectedEngine.latest_reading)
      .then(setPrediction)
      .catch((err) => setError(err.message));
  }, [selectedEngine]);

  return (
    <div className="app">
      <header>
        <h1>🛩️ Engine Health Platform</h1>
        <p className="subtitle">
          Prédiction de durée de vie utile restante (RUL) et détection d'anomalies
          pour une flotte de démonstration de moteurs d'avion.
        </p>
      </header>

      {error && <div className="error-banner">⚠ {error}</div>}

      <section className="controls">
        <label htmlFor="engine-select">Unité moteur :</label>
        <select
          id="engine-select"
          disabled={loadingEngines || engines.length === 0}
          value={selectedId ?? ""}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {engines.map((engine) => (
            <option key={engine.engine_id} value={engine.engine_id}>
              {engine.engine_id} (cycle {engine.current_cycle})
            </option>
          ))}
        </select>
      </section>

      {selectedEngine && (
        <section className="cards">
          <div className={`card ${prediction?.is_anomaly ? "card-anomaly" : "card-ok"}`}>
            <h2>RUL prédit</h2>
            <p className="big-number">
              {(prediction ?? selectedEngine).predicted_rul?.toFixed(0)}
              <span className="unit"> cycles</span>
            </p>
            <p className="anomaly-flag">
              {(prediction ?? selectedEngine).is_anomaly
                ? "🔴 Anomalie détectée"
                : "🟢 Fonctionnement nominal"}
            </p>
          </div>

          <div className="card">
            <h2>Dernière lecture (cycle {selectedEngine.current_cycle})</h2>
            <ul className="sensor-list">
              <li>Température : {selectedEngine.latest_reading.sensor_temp.toFixed(1)}</li>
              <li>Pression : {selectedEngine.latest_reading.sensor_pressure.toFixed(2)}</li>
              <li>Vibration : {selectedEngine.latest_reading.sensor_vibration.toFixed(3)}</li>
              <li>Débit carburant : {selectedEngine.latest_reading.sensor_fuel_flow.toFixed(2)}</li>
            </ul>
            {prediction?.sensor_z_scores && (
              <p className="z-score-hint">
                z-score max : {prediction.max_abs_z_score.toFixed(2)}
              </p>
            )}
          </div>
        </section>
      )}

      <section className="chart-section">
        <h2>Historique des cycles ({selectedId ?? "…"})</h2>
        {loadingHistory && <p>Chargement de l'historique…</p>}
        {!loadingHistory && history.length > 0 && (
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={history} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="cycle" label={{ value: "Cycle", position: "insideBottom", offset: -2 }} />
              <YAxis yAxisId="left" label={{ value: "RUL prédit", angle: -90, position: "insideLeft" }} />
              <YAxis yAxisId="right" orientation="right" label={{ value: "Température", angle: 90, position: "insideRight" }} />
              <Tooltip />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="predicted_rul"
                name="RUL prédit"
                stroke="#2563eb"
                dot={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="sensor_temp"
                name="Température"
                stroke="#dc2626"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>

      <footer>
        <p>
          Backend : FastAPI + scikit-learn (RandomForestRegressor) · Frontend : React + Vite +
          recharts · Modèle entraîné sur des données synthétiques (voir README).
        </p>
      </footer>
    </div>
  );
}

export default App;
