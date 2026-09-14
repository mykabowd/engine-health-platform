# Journal de dépannage (diagnostics rencontrés pendant ce projet)

Ce fichier documente honnêtement les problèmes réellement rencontrés pendant
le développement/déploiement de ce projet, et comment ils ont été
diagnostiqués et résolus - dans une logique de documentation honnête des
problèmes réels liés aux conteneurs, aux dépendances, aux configurations et
aux environnements Kubernetes.

## 1. `NodePort` injoignable depuis l'hôte macOS sur un cluster k3d

**Symptôme** : après un premier `k3d cluster create engine-health` (sans
options de port) puis `helm install`, `kubectl get svc` affiche bien
`engine-health-web  NodePort  ...  80:30080/TCP`, les pods sont
`Running`/`1/1 Ready`, mais `curl http://localhost:30080/` échoue
(connexion refusée / timeout), y compris en ciblant directement l'IP interne
du nœud (`172.18.0.3:30080`, elle-même seulement routable depuis le réseau
Docker de Colima, pas depuis l'hôte macOS).

**Diagnostic** : les nœuds k3d sont eux-mêmes des conteneurs Docker
(exécutés ici dans la VM Colima). Un `NodePort` n'est exposé que sur
l'interface réseau du *conteneur du nœud*, pas automatiquement republié sur
l'hôte - `k3d` ne mappe des ports hôte que pour ceux explicitement déclarés
à la création du cluster (ou via le load balancer intégré pour 80/443 par
défaut dans certains cas). `k3d cluster create --help` confirme l'option
`-p, --port` (format `HOST:CONTAINER@NODEFILTER`, ex.
`-p "30080:30080@server:0"`) pour republier un port du nœud sur l'hôte.

**Correction appliquée** :

```bash
helm uninstall engine-health
k3d cluster delete engine-health
k3d cluster create engine-health -p "30080:30080@server:0" --wait
k3d image import engine-health-api:0.1.0 engine-health-web:0.1.0 -c engine-health
helm install engine-health ./helm/engine-health-platform
```

Après cette correction, `curl http://localhost:30080/` et
`curl http://localhost:30080/api/health` répondent correctement (voir
`docs/k8s-verification.md` pour les sorties complètes).

**Alternative non retenue** : `kubectl port-forward svc/engine-health-web
8080:80` aurait aussi permis de vérifier le service sans recréer le cluster,
mais ne teste pas réellement le chemin `NodePort` déclaré dans le chart -
la correction du mapping de port au niveau du cluster a été préférée pour
vérifier fidèlement ce que `values.yaml` déclare.

## 2. Taille de l'artefact du modèle (`model.joblib`)

**Symptôme** : un premier entraînement avec
`RandomForestRegressor(n_estimators=80, max_depth=8)` produisait un artefact
`joblib` de ~905 Ko - trop volumineux pour un fichier volontairement
committé dans un repo Git ("quelques centaines de Ko max" visé).

**Diagnostic** : la taille d'un `RandomForestRegressor` sérialisé croît
avec le nombre d'arbres et leur profondeur (chaque arbre stocke sa propre
structure de nœuds/seuils).

**Correction** : réduction à `n_estimators=25, max_depth=6,
min_samples_leaf=20` et compression `joblib.dump(..., compress=("gzip", 9))`
(au lieu de `compress=3`). Résultat : artefact de **75,6 Ko**, avec une
MAE de test qui reste raisonnable (~22,7 cycles sur une durée de vie
simulée de 120 à 360 cycles) pour un projet de démonstration.

## 3. `docker compose` non disponible par défaut

**Symptôme** : `docker compose build` échouait avec `docker: unknown
command: docker compose`, bien que `docker` (via Colima) fonctionne.

**Diagnostic** : le plugin CLI `docker compose` n'était pas installé
séparément (Colima ne l'inclut pas par défaut) et `~/.docker/config.json` ne
référençait aucun répertoire de plugins additionnel.

**Correction** : `brew install docker-compose`, puis ajout de
`"cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"]` dans
`~/.docker/config.json` (repris du message d'avertissement affiché par
Homebrew après l'installation). `docker compose version` fonctionne ensuite
normalement.

## Ce qui a fonctionné du premier coup (pas de problème rencontré)

- CoreDNS / résolution DNS interne au cluster (le proxy nginx résout
  correctement `engine-health-api` vers le bon `ClusterIP`).
- Le pull/l'usage des images `python:3.11-slim`, `node:22-alpine`,
  `nginx:alpine` (aucun souci de tirage d'image, réseau Colima fonctionnel).
- `helm lint` et `helm template` : aucune erreur de rendu la première fois.
- Les *readiness/liveness probes* (`/health` pour l'API, `/` pour le
  frontend) : les deux pods sont passés à `Running` puis `1/1 Ready` sans
  redémarrage.
