# Preuve de déploiement Kubernetes réel (k3d + Helm)

Ce fichier documente une exécution **réelle** du déploiement décrit dans le
README, exécutée le 2026-09-06, avec les sorties de commandes obtenues
pendant que le cluster tournait. Le cluster a été détruit après vérification
(`k3d cluster delete engine-health`) pour ne laisser aucune ressource active.

## Environnement

- macOS Apple Silicon, Docker via Colima (`unix:///Users/akmax/.colima/default/docker.sock`)
- `k3d` v5.9.0, `kubectl` v1.37.0 (client) / serveur `v1.35.5+k3s1`, `helm` v4.2.4
  (installés via `brew install k3d kubectl helm` pour ce projet)

## 1. Création du cluster

```bash
k3d cluster create engine-health -p "30080:30080@server:0" --wait
```

**Note de dépannage (voir aussi `docs/troubleshooting.md`)** : la première
tentative a créé le cluster *sans* mapping de port explicite. Le `Service`
`web` de type `NodePort` (port 30080) était bien actif côté cluster
(`kubectl get svc` le montrait), mais **injoignable depuis l'hôte**
(`curl http://localhost:30080/` → timeout / connection refused), car les
nœuds k3d tournent dans des conteneurs Docker et le port du nœud n'est pas
automatiquement republié sur l'hôte. Diagnostic : `k3d cluster create --help`
confirme qu'il faut déclarer un mapping de port au moment de la création du
cluster (`-p "HOST:CONTAINER@server:0"`). Correction : cluster détruit et
recréé avec `-p "30080:30080@server:0"`, qui republie le port du nœud
`server-0` sur le port 30080 de l'hôte. Après cette correction, `curl
http://localhost:30080/` répond bien (voir section 4 ci-dessous).

```
INFO Cluster 'engine-health' created successfully!
```

```bash
kubectl get nodes -o wide
```

```
NAME                         STATUS   ROLES           AGE   VERSION        INTERNAL-IP   CONTAINER-RUNTIME
k3d-engine-health-server-0   Ready    control-plane   15s   v1.35.5+k3s1   172.18.0.3    containerd://2.2.3-k3s1
```

## 2. Import des images Docker construites localement

```bash
k3d image import engine-health-api:0.1.0 engine-health-web:0.1.0 -c engine-health
```

```
INFO Importing image(s) into cluster 'engine-health'
INFO Saving 2 image(s) from runtime...
INFO Importing images into nodes...
INFO Successfully imported 2 image(s) into 1 cluster(s)
```

## 3. `helm install`

```bash
helm install engine-health ./helm/engine-health-platform
```

```
NAME: engine-health
LAST DEPLOYED: Sun Sep  6 03:53:10 2026
NAMESPACE: default
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
```

```bash
kubectl rollout status deployment/engine-health-api --timeout=90s
kubectl rollout status deployment/engine-health-web --timeout=90s
```

```
deployment "engine-health-api" successfully rolled out
deployment "engine-health-web" successfully rolled out
```

```bash
kubectl get pods -o wide
```

```
NAME                                 READY   STATUS    RESTARTS   AGE   IP           NODE
engine-health-api-76874b9956-j8xf8   1/1     Running   0          8s    10.42.0.9    k3d-engine-health-server-0
engine-health-web-7c776f59f-zs5v2    1/1     Running   0          8s    10.42.0.10   k3d-engine-health-server-0
```

```bash
kubectl get svc
```

```
NAME                TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
engine-health-api   ClusterIP   10.43.53.177   <none>        8000/TCP       19s
engine-health-web   NodePort    10.43.133.76   <none>        80:30080/TCP   19s
kubernetes          ClusterIP   10.43.0.1      <none>        443/TCP        54s
```

```bash
kubectl get deploy
```

```
NAME                READY   UP-TO-DATE   AVAILABLE   AGE
engine-health-api   1/1     1            1           19s
engine-health-web   1/1     1            1           19s
```

```bash
helm list
```

```
NAME         	NAMESPACE	REVISION	STATUS  	CHART                       	APP VERSION
engine-health	default  	1       	deployed	engine-health-platform-0.1.0	0.1.0
```

## 4. Vérification réelle de l'API via `curl` (port NodePort 30080)

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:30080/
```
```
HTTP 200
```

```bash
curl -s http://localhost:30080/api/health
```
```json
{"status":"ok","model_loaded":true,"sensor_names":["sensor_temp","sensor_pressure","sensor_vibration","sensor_fuel_flow"]}
```

```bash
curl -s http://localhost:30080/api/engines
```
```json
{"engines":[{"engine_id":"ENG-001","current_cycle":259,"latest_reading":{"cycle":259.0,"sensor_temp":682.76,"sensor_pressure":24.06,"sensor_vibration":1.09,"sensor_fuel_flow":10.11},"predicted_rul":27.84,"is_anomaly":true}, ...]}
```

```bash
curl -s -X POST http://localhost:30080/api/predict \
  -H "Content-Type: application/json" \
  -d '{"cycle":10,"sensor_temp":641,"sensor_pressure":29.9,"sensor_vibration":0.36,"sensor_fuel_flow":8.1}'
```
```json
{"predicted_rul":222.72,"is_anomaly":false,"max_abs_z_score":0.39,"sensor_z_scores":{"sensor_temp":0.3,"sensor_pressure":-0.13,"sensor_vibration":0.16,"sensor_fuel_flow":0.39}}
```

This confirms end-to-end connectivity through the full path: host →
k3d NodePort (30080) → `web` Service → nginx pod (reverse proxy `/api/*`) →
`api` ClusterIP Service → FastAPI pod → RandomForestRegressor model.

## 5. Nettoyage

```bash
helm uninstall engine-health
k3d cluster delete engine-health
```

Le cluster a été détruit après cette vérification. Aucune ressource k3d ne
tourne en permanence pour ce projet.
