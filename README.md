# PulseBoard

Stack de observabilidad para Kubernetes: una API en FastAPI instrumentada con métricas
Prometheus, con Grafana para dashboards, Loki para logs centralizados y Alertmanager
para alertas — el mismo tipo de stack que usan equipos de infraestructura en producción.

> Este README se actualiza a medida que avanza el proyecto. Refleja el estado real del
> repositorio en cada momento, no un plan aspiracional.

## Estado actual — Fases 1, 2, 3, 4 y 5 completadas ✅

### Qué funciona ahora mismo

- API en **FastAPI**, instrumentada automáticamente con `prometheus-fastapi-instrumentator`,
  exponiendo métricas en formato Prometheus.
- Empaquetada en una imagen **Docker** propia (`app/Dockerfile`).
- Desplegada en **Kubernetes** (namespace `pulseboard`) como un `Deployment` de 3 réplicas
  + un `Service` — verificado corriendo en minikube, con los 3 Pods en estado
  `Running`/`Ready`.
- **Prometheus** instalado vía Helm (`kube-prometheus-stack`, namespace `monitoring`),
  corriendo como `StatefulSet` con almacenamiento persistente (10Gi, retención 15 días).
- Descubrimiento automático de los Pods de `pulseboard-api` vía anotaciones
  (`prometheus.io/scrape|port|path`) — verificado en la UI de Prometheus
  (`Status → Targets`): 3 targets `UP`, uno por réplica.
- **Alertmanager** también quedó instalado como parte del mismo chart (como `StatefulSet`;
  sus reglas de alerta propias son la Fase 5).
- **Dashboard de Grafana propio** ("PulseBoard API") cargado automáticamente vía
  `ConfigMap` con la label `grafana_dashboard: "1"` (sin tocar la UI a mano) — 4 paneles:
  request rate, latencia P95, error rate, y logs en vivo. Verificado con tráfico real
  generado por `hey` (3,774 requests, 100% `200 OK`, P95 ~289ms).
- **Loki** instalado vía Helm (`grafana/loki`, modo `SingleBinary`, namespace `monitoring`)
  con almacenamiento en filesystem (PVC de 5Gi) — sin las cachés `memcached` opcionales
  del chart, apagadas a propósito por límites de memoria del cluster local.
- **Promtail** instalado vía Helm (`grafana/promtail`) como `DaemonSet` — descubre y
  recolecta automáticamente los logs de todos los Pods del cluster (sin anotaciones
  manuales) y los envía a Loki.
- **Loki registrado como datasource de Grafana** vía `ConfigMap` con la label
  `grafana_datasource: "1"` (mismo patrón "todo como código" que el dashboard) —
  verificado con logs reales de `pulseboard-api` visibles tanto en Grafana Explore
  (LogQL) como en el panel de logs del dashboard.
- **Reglas de alerta** (`PrometheusRule`, CRD del Prometheus Operator) para
  `HighErrorRate` (error rate > 5%) y `PodCrashLooping` — verificadas cargando y
  evaluando correctamente (`Status → Rules` en Prometheus, ambas en `OK`). El receiver
  de Alertmanager queda como `"null"` por defecto (confirmado inspeccionando el Secret
  real que genera Helm) — las alertas se verifican vía UI, sin depender de un Slack real.

### Endpoints disponibles

| Endpoint | Descripción |
|---|---|
| `GET /` | Estado básico del servicio |
| `GET /health` | Usado por el `readinessProbe` del Deployment |
| `GET /items/{item_id}` | Endpoint de ejemplo con latencia variable simulada (para ver variación en dashboards de latencia más adelante) |
| `GET /metrics` | Métricas en formato Prometheus (requests, latencia, y métricas de proceso de Python) |

### Stack técnico usado hasta ahora

- Python 3.12 · FastAPI · Uvicorn · prometheus-fastapi-instrumentator
- Docker
- Kubernetes (minikube, local)
- Helm 3 · `kube-prometheus-stack` (Prometheus, Alertmanager, Grafana, kube-state-metrics,
  node-exporter, Prometheus Operator)
- Helm 3 · `grafana/loki` (modo `SingleBinary`) + `grafana/promtail`
- `hey` (generador de carga HTTP, usado para poblar los dashboards con tráfico real)

### Cómo correr la API localmente

```powershell
python -m venv venv
.\venv\Scripts\Activate
pip install -r app/requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Cómo desplegarla en minikube

```powershell
minikube start --cpus=4 --memory=6144
minikube docker-env --shell powershell | Invoke-Expression
docker build -t pulseboard-api:latest ./app
kubectl apply -f k8s/api-deployment.yaml
kubectl port-forward -n pulseboard svc/pulseboard-api 8000:80
```

### Cómo instalar Prometheus (Helm)

```powershell
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
kubectl create namespace monitoring
helm install prometheus prometheus-community/kube-prometheus-stack `
  --namespace monitoring `
  --values helm-values/prometheus-values.yaml
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

### Cómo ver el dashboard de Grafana y generar tráfico de prueba

```powershell
kubectl apply -f k8s/grafana-dashboard-configmap.yaml
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# http://localhost:3000 — admin / pulseboard123 — Dashboards → "PulseBoard API"

# En otra terminal, con el port-forward de la API activo (puerto 8000):
hey -z 60s -c 10 http://localhost:8000/items/5
```

### Cómo instalar Loki + Promtail y ver logs en Grafana

```powershell
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
helm install loki grafana/loki -n monitoring --values helm-values/loki-values.yaml
helm install promtail grafana/promtail -n monitoring --values helm-values/promtail-values.yaml

kubectl apply -f k8s/grafana-loki-datasource-configmap.yaml
kubectl apply -f k8s/grafana-dashboard-configmap.yaml
# Grafana → Explore → datasource "Loki":
# {namespace="pulseboard", app="pulseboard-api"}
```

### Cómo aplicar y verificar las reglas de alerta

```powershell
kubectl apply -f k8s/alert-rules.yaml
kubectl get prometheusrule -n pulseboard
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
# http://localhost:9090 → Status → Rules → grupo "pulseboard.api"

# Inspeccionar el receiver real que Helm generó para Alertmanager:
$b64 = kubectl get secret -n monitoring alertmanager-prometheus-kube-prometheus-alertmanager -o jsonpath="{.data.alertmanager\.yaml}"
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($b64))
```

## Roadmap — lo que falta

### RBAC para Prometheus (pendiente)
- `ClusterRole` + `ClusterRoleBinding` para que Prometheus pueda descubrir Pods y
  Services en todos los namespaces del cluster, no solo en `monitoring`.

### Cierre de portafolio (pendiente)
- Capturas de Grafana y Loki con tráfico real generado (`hey`).
- Diagrama de arquitectura del stack completo.
- Sección de "decisiones técnicas": por qué StatefulSet para Prometheus, por qué
  DaemonSet para Promtail, por qué ClusterRole para el RBAC.

## Decisiones técnicas

### Contraseña de Grafana en texto plano

`helm-values/prometheus-values.yaml` fija `grafana.adminPassword` como texto plano, y
ese archivo sí está versionado en git. Es una simplificación deliberada para este
proyecto: el cluster es 100% local (minikube, nunca expuesto a internet) y la
contraseña es desechable, solo para desarrollo/aprendizaje. **En un entorno de
producción real esto no se haría así** — se usaría un `Secret` de Kubernetes
(referenciado vía `grafana.admin.existingSecret` en el chart) para que la contraseña
real nunca quede en texto plano dentro del repositorio.

### Loki en modo `SingleBinary`, sin cachés y sin multi-tenancy

`helm-values/loki-values.yaml` fuerza `deploymentMode: SingleBinary` (un solo Pod hace
ingestión, almacenamiento y consultas) en vez del modo distribuido por defecto del chart
(`read`/`write`/`backend`/`gateway`/`MinIO` separados), y además desactiva las cachés
`memcached` opcionales (`chunksCache`/`resultsCache`): en un cluster local de un solo
nodo con memoria limitada, esas cachés (que piden ~10Gi cada una) nunca lograban
agendarse. También se desactiva `auth_enabled` (multi-tenancy), ya que exigir el header
`X-Scope-OrgID` en cada llamada solo tiene sentido cuando varios equipos comparten un
mismo Loki — no aplica a un cluster de aprendizaje de un solo inquilino. **En un entorno
de producción real con múltiples nodos**, el modo distribuido y las cachés sí aportan
valor real de escalabilidad y rendimiento.

## Conceptos de Kubernetes cubiertos en este proyecto

- `Deployment` vs `StatefulSet` (identidad estable, almacenamiento persistente).
- `DaemonSet` (un Pod por nodo).
- `Helm` como gestor de paquetes de Kubernetes.
- Service discovery basado en anotaciones de Pod para Prometheus.
- Patrón *sidecar* (config-reloader de Prometheus/Alertmanager, dashboard-loader de
  Grafana) para recarga en caliente sin reiniciar el proceso principal.
- Dashboards y datasources de Grafana como código (`ConfigMap` + label, sin crear nada
  a mano en la UI).
- Métricas de Prometheus: `Counter` + `rate()`, `Histogram` + `histogram_quantile()`.
- `PrometheusRule` (CRD) y la máquina de estados de una alerta (`inactive` →
  `pending` → `firing`, controlada por `for:`).
- Enrutamiento y supresión de alertas en Alertmanager (`route`, `receiver`,
  `inhibit_rules`).
- Logs centralizados con Loki y LogQL (`{label="valor"}`, filtros `|=`), y cómo Promtail
  etiqueta cada línea automáticamente con metadata del Pod (namespace, labels).
- `RBAC`: `Role`/`RoleBinding` (por namespace) vs `ClusterRole`/`ClusterRoleBinding`
  (todo el cluster).
