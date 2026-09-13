🇬🇧 [English version](README.md)

# engine-health-platform

Service **full-stack** de "santé moteur" : une API Python (FastAPI) prédit
la durée de vie utile restante (**RUL**, *Remaining Useful Life*) d'unités
moteur d'avion à partir de lectures capteurs, et un frontend React affiche
la flotte de démonstration, la prédiction courante et l'historique des
cycles. Le tout est conteneurisé, et a été **réellement déployé et vérifié**
sur un cluster Kubernetes local (`k3d` + `Helm`) — pas seulement écrit.

Continuité thématique avec [`ml-critical-systems-lab`](../ml-critical-systems-lab)
(maintenance prédictive sur données NASA C-MAPSS) : même domaine
(dégradation de moteurs d'avion), mais ici exposé comme un **service** réel
(API + frontend + Docker + Kubernetes), et non plus seulement une étude
hors-ligne (notebooks/rapport).

## Pourquoi ce projet

Ce projet a été construit pour démontrer, de façon honnête et vérifiable,
des compétences **full-stack** (API Python, frontend React,
conteneurisation, déploiement Kubernetes réel, CI/CD) pour des rôles de
développeur logiciel full-stack — des compétences qui n'étaient pas encore
démontrées par mes deux autres projets portfolio :

| Compétence visée | Où c'est démontré ici |
|---|---|
| Développer des services backend, API, microservices en Python | `backend/` — API FastAPI complète (4 endpoints, Pydantic, tests) |
| Interfaces légères, prototypes web, démonstrateurs | `frontend/` — SPA React/Vite avec graphique |
| Intégrer frontend, backend, services IA (modèle ML), BDD/API | Frontend → nginx (reverse proxy) → API FastAPI → modèle scikit-learn |
| Créer/maintenir/optimiser des images Docker | `backend/Dockerfile`, `frontend/Dockerfile` (multi-stage) |
| Développer/maintenir des Helm charts pour Kubernetes | `helm/engine-health-platform/` — **réellement installé** via `helm install` sur un cluster k3d |
| Automatiser déploiements/configurations/environnements | `Makefile` (cibles `k8s-deploy`, `k8s-verify`, `k8s-destroy`), `.gitlab-ci.yml` |
| Diagnostiquer/résoudre des problèmes Kubernetes | `docs/troubleshooting.md` — un vrai problème de connectivité `NodePort` rencontré et corrigé (voir plus bas) |
| Frameworks frontend modernes (React, Angular...) | React 19 + Vite + recharts |
| Outils CI/CD (GitLab CI) | `.gitlab-ci.yml` — 4 stages, syntaxiquement valide (non exécuté sur un runner réel, voir section CI/CD) |

Ce que mes deux autres projets démontraient déjà et que ce projet ne
répète **pas** en détail : RAG/LLM/agents/MCP (`genai-mcp-assistant`), ML
classique approfondi sur données réelles NASA C-MAPSS avec rapport
technique (`ml-critical-systems-lab`). Ici, le modèle ML est volontairement
simple (un `RandomForestRegressor` sur données synthétiques) — l'objectif
de *ce* projet est l'intégration full-stack + Kubernetes, pas la recherche
en ML.

## Stack technique

- **Backend** : Python 3.11, FastAPI, Pydantic, scikit-learn, numpy, joblib
- **Frontend** : React 19, Vite, recharts
- **Conteneurisation** : Docker (images multi-stage), docker-compose
- **Kubernetes** : Helm (chart complet), déployé et vérifié sur `k3d`
- **CI/CD** : GitLab CI (`.gitlab-ci.yml` — lint / test / build / deploy)
- **Tests** : pytest + `fastapi.testclient.TestClient` (11 tests)

## Architecture

```
┌──────────────────┐   GET /               ┌──────────────────────┐
│  Navigateur       │   GET/POST /api/*     │  nginx (web pod)      │
│  (SPA React)       │ ───────────────────► │  - sert dist/ (React) │
└──────────────────┘                        │  - proxy /api/* → api │
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
                                             │  (données synthétiques, │
                                             │   voir train.py)         │
                                             └──────────────────────┘
```

En local (docker-compose) et sur Kubernetes (Helm), la topologie est
identique : deux composants (`api`, `web`), le frontend appelle toujours
`/api/*` en same-origin, et c'est nginx qui route vers le service `api` —
voir la section **Choix CORS vs reverse proxy** ci-dessous pour le détail.

### Choix CORS vs reverse proxy

Le frontend appelle toujours `/api/*` en **same-origin** (pas d'URL absolue
codée en dur) :

- En **production / Docker / Kubernetes**, nginx reverse-proxy `/api/*`
  vers le service backend (`frontend/nginx.conf` en local,
  `helm/.../templates/web-nginx-configmap.yaml` sur Kubernetes avec le
  vrai nom du Service). Le navigateur ne fait donc **jamais** de requête
  cross-origin dans ce chemin — pas de configuration CORS à faire confiance
  côté client.
- En **développement local** (`npm run dev`, Vite sur `:5173`, API sur
  `:8000`, sans proxy), le frontend appelle directement
  `http://localhost:8000` (via `VITE_API_URL`, voir `frontend/.env.development`)
  et c'est là que le middleware CORS de FastAPI (`backend/src/engine_health/main.py`)
  entre en jeu, pour que `npm run dev` fonctionne sans lancer nginx.

Les deux mécanismes coexistent donc, mais pour des raisons différentes et
complémentaires — le proxy est la solution "robuste" retenue pour tout
déploiement réel ; CORS est un confort de développement local uniquement.

## Démarrage rapide (local, sans Kubernetes)

### Backend seul (venv)

```bash
make backend-install   # crée backend/.venv, installe les dépendances
make backend-train      # (ré)entraîne le modèle -> backend/src/engine_health/artifacts/model.joblib
make backend-test        # pytest -v (11 tests)
make backend-run          # uvicorn --reload sur :8000
```

Le modèle est déjà committé dans le repo (`model.joblib`, ~76 Ko) : `make
backend-train` n'est nécessaire que si vous voulez le régénérer.

### Frontend seul (dev server Vite)

```bash
make frontend-install
make frontend-dev   # http://localhost:5173, appelle http://localhost:8000 (VITE_API_URL)
```

### Les deux ensemble via Docker Compose (recommandé)

```bash
make docker-up
# équivalent à : docker compose up --build
```

Puis :

```bash
curl http://localhost:8000/health          # API directe
curl http://localhost:8080/api/engines      # via nginx (frontend)
open http://localhost:8080                   # SPA React
```

Arrêt : `make docker-down` (= `docker compose down -v`).

**Vérifié réellement** le 2026-09-06 : `docker compose build` (2 images
construites), `docker compose up -d` (2 conteneurs `healthy`), puis :
- `curl http://localhost:8000/health` → `{"status":"ok","model_loaded":true,...}`
- `curl http://localhost:8080/api/engines` → liste de 6 unités moteur avec RUL prédit
- `curl -X POST http://localhost:8080/api/predict -d '{...}'` → prédiction + flag d'anomalie
- `curl http://localhost:8080/` → `HTTP 200` (page React servie par nginx)

## Démarrage rapide (Kubernetes local, k3d + Helm)

Prérequis installés pour ce projet : `brew install k3d kubectl helm`
(Docker déjà disponible via Colima).

```bash
make k8s-deploy   # crée le cluster k3d, build+importe les images, helm install, attend le rollout
make k8s-verify    # kubectl get pods/svc + curl sur le NodePort 30080
make k8s-destroy    # helm uninstall + k3d cluster delete (nettoyage complet)
```

Ou étape par étape :

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

**Ce déploiement a été réellement exécuté et vérifié** le 2026-09-06 (cluster
détruit ensuite pour ne rien laisser tourner). Sorties complètes de
`kubectl get pods`, `kubectl get svc`, `helm install`, et des `curl` de
vérification : voir **[`docs/k8s-verification.md`](docs/k8s-verification.md)**.

Un vrai problème de connectivité a été rencontré et corrigé pendant ce
déploiement (le `NodePort` n'était pas joignable depuis l'hôte macOS sans
mapping de port explicite à la création du cluster k3d) : diagnostic complet
dans **[`docs/troubleshooting.md`](docs/troubleshooting.md)**.

### Pourquoi NodePort plutôt qu'un Ingress

Un `Service` de type `NodePort` a été choisi plutôt qu'une ressource
`Ingress` : cela donne un point d'accès externe directement `curl`-able sans
installer et configurer un contrôleur Ingress supplémentaire
(nginx-ingress, Traefik...) sur le cluster local — une dépendance
supplémentaire à opérer, pas nécessaire pour démontrer les compétences
visées (écriture et déploiement réel d'un chart Helm). Voir
`helm/engine-health-platform/values.yaml`.

## Structure du projet

```
engine-health-platform/
├── backend/
│   ├── src/engine_health/
│   │   ├── config.py         # configuration centralisée (env vars)
│   │   ├── data_gen.py         # générateur de données synthétiques de dégradation
│   │   ├── train.py             # entraîne le RandomForestRegressor -> model.joblib
│   │   ├── model.py              # chargement du modèle + prédiction + détection d'anomalie
│   │   ├── demo_data.py           # flotte de démo en mémoire (seed fixe)
│   │   ├── schemas.py              # modèles Pydantic (requêtes/réponses)
│   │   ├── main.py                  # application FastAPI (4 endpoints)
│   │   └── artifacts/model.joblib    # modèle entraîné, committé (~76 Ko)
│   ├── tests/test_api.py               # 11 tests pytest (TestClient)
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # page unique : sélecteur, cartes RUL/anomalie, graphique
│   │   ├── api.js               # wrapper fetch (VITE_API_URL configurable)
│   │   └── ...
│   ├── nginx.conf                # reverse-proxy /api/* (config par défaut, docker-compose)
│   └── Dockerfile                 # multi-stage : node (build) -> nginx (serve)
├── helm/engine-health-platform/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/                  # Deployment+Service (api, web), ConfigMap nginx
├── docs/
│   ├── k8s-verification.md          # preuves du déploiement k3d/Helm réel
│   └── troubleshooting.md            # problèmes rencontrés et corrigés
├── docker-compose.yml
├── .gitlab-ci.yml                     # pipeline lint/test/build/deploy
├── Makefile
└── .gitignore
```

## CI/CD — GitLab CI

Un `.gitlab-ci.yml` complet est fourni avec 4 stages :

1. **lint** : `ruff` sur le backend, `npm run lint` (oxlint) sur le frontend
2. **test** : `pytest` sur le backend (avec rapport JUnit en artefact)
3. **build** : `docker build` des 2 images, poussées vers `$CI_REGISTRY_IMAGE`
   (registre de conteneurs GitLab intégré)
4. **deploy** : stage `when: manual`, qui **documente en commentaires**
   comment un `helm upgrade --install` serait exécuté contre un cluster réel

**Honnêteté** : ce pipeline **n'a pas été exécuté sur un vrai runner GitLab**
(aucun compte/projet GitLab connecté dans ce contexte de projet portfolio
local). Il a été vérifié comme suit :
- YAML syntaxiquement valide (parsé avec `PyYAML`)
- Chaque commande individuelle (`ruff check`, `pytest`, `npm run lint`,
  `docker build`) a été **réellement exécutée en local** avec succès (voir
  sections précédentes) — le pipeline assemble ces mêmes commandes dans la
  syntaxe GitLab CI standard, mais l'exécution bout-en-bout sur un runner
  n'a pas été testée.

## Ce que ce projet démontre (et ce qu'il ne démontre pas)

**Démontre** :
- Développement d'une API Python (FastAPI) avec plusieurs endpoints,
  validation Pydantic, tests automatisés (pytest, 11 tests verts)
- Développement d'un frontend React (Vite) consommant cette API,
  graphique de données (recharts), configuration par variable d'env
- Conteneurisation Docker multi-services (image Python légère, build
  multi-stage node→nginx), orchestrées via docker-compose
- Écriture **et déploiement réel vérifié** d'un chart Helm sur un cluster
  Kubernetes local (k3d) : `helm install`, pods `Running`/`Ready`, service
  `NodePort` interrogé avec succès via `curl`
- Diagnostic et correction d'un vrai problème de connectivité Kubernetes
  (NodePort/k3d), documenté avec la cause et la correction exacte
- Structure d'un pipeline CI/CD GitLab (stages lint/test/build/deploy)
  suivant les pratiques standards

**Ne démontre PAS** (à ne pas sur-vendre sur un CV) :
- Exécution réelle du pipeline CI/CD sur un runner GitLab connecté (pas de
  compte GitLab utilisé ici — voir section CI/CD ci-dessus)
- Contrôleur Ingress, TLS, ou tout "production hardening" (le NodePort est
  une solution volontairement simple pour un cluster de démo local)
- Autoscaling (HPA), haute disponibilité multi-nœuds/multi-réplicas réelle
  (le chart supporte `replicaCount` mais n'a été testé qu'avec 1 réplica
  par composant sur un cluster à un seul nœud)
- Authentification/autorisation applicative (aucun endpoint n'est protégé —
  ce n'est pas un système de production, mais une démo)
- Un modèle de ML sophistiqué ou entraîné sur des données réelles NASA
  C-MAPSS (voir `ml-critical-systems-lab` pour ce volet) : ici, données
  100% synthétiques générées par `numpy`, modèle `RandomForestRegressor`
  volontairement simple — l'objectif est l'intégration full-stack, pas la
  performance du modèle

## Limites connues / pistes d'amélioration

- Pas de base de données réelle : la "flotte" de démonstration est générée
  en mémoire au démarrage du process (seed fixe), pas persistée.
- Le modèle n'est pas ré-entraîné automatiquement en CI (pas de pipeline de
  ML/MLOps) — `model.joblib` est un artefact statique committé.
- Le graphique frontend n'affiche que l'historique déjà connu de chaque
  unité de démo ; pas de simulation "en direct" de nouveaux cycles.
- Un seul type de modèle testé (RandomForestRegressor) ; pas de comparaison
  d'algorithmes (ce n'est pas l'objectif de ce projet, voir
  `ml-critical-systems-lab` pour ce type de travail).
