# PulseBoard

Stack de observabilidad para Kubernetes: una API en FastAPI instrumentada con métricas
Prometheus, con Grafana para dashboards, Loki para logs centralizados y Alertmanager
para alertas — el mismo tipo de stack que usan equipos de infraestructura en producción.

> Este README se actualiza a medida que avanza el proyecto. Refleja el estado real del
> repositorio en cada momento, no un plan aspiracional.

## Estado actual — Fase 1 completada ✅

### Qué funciona ahora mismo

- API en **FastAPI**, instrumentada automáticamente con `prometheus-fastapi-instrumentator`,
  exponiendo métricas en formato Prometheus.
- Empaquetada en una imagen **Docker** propia (`app/Dockerfile`).
- Desplegada en **Kubernetes** (namespace `pulseboard`) como un `Deployment` de 3 réplicas
  + un `Service` — verificado corriendo en minikube, con los 3 Pods en estado
  `Running`/`Ready`.

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

## Roadmap — lo que falta

### Fase 2 — Helm y Prometheus (pendiente)
- Instalar Helm 3.
- Instalar `kube-prometheus-stack` vía Helm en un namespace `monitoring` separado.
- Configurar `additionalScrapeConfigs` para que Prometheus descubra los Pods de
  `pulseboard-api` usando las anotaciones `prometheus.io/scrape|port|path` ya presentes
  en el Deployment.
- Verificar en la UI de Prometheus (`Status → Targets`) que `pulseboard-api` aparece `UP`.

### Fase 3 — Grafana y dashboards como código (pendiente)
- Grafana se instala junto con el chart de Prometheus.
- Dashboard propio como `ConfigMap` versionado en Git (no creado a mano desde la UI):
  request rate, latencia P95, error rate.

### Fase 4 — Loki + Promtail, logs centralizados (pendiente)
- Instalar `loki-stack` vía Helm (Promtail corre como `DaemonSet`, un Pod por nodo).
- Consultar logs de todos los Pods desde Grafana Explore usando LogQL.

### Fase 5 — Alertmanager y reglas de alerta (pendiente)
- Reglas `PrometheusRule`: `HighErrorRate` (error rate > 5%) y `PodCrashLooping`.
- Enrutamiento de alertas verificado vía UI de Alertmanager (o `webhook.site` para
  capturas de portafolio), sin depender de un Slack real.

### RBAC para Prometheus (pendiente)
- `ClusterRole` + `ClusterRoleBinding` para que Prometheus pueda descubrir Pods y
  Services en todos los namespaces del cluster, no solo en `monitoring`.

### Cierre de portafolio (pendiente)
- Capturas de Grafana y Loki con tráfico real generado (`hey`).
- Diagrama de arquitectura del stack completo.
- Sección de "decisiones técnicas": por qué StatefulSet para Prometheus, por qué
  DaemonSet para Promtail, por qué ClusterRole para el RBAC.

## Conceptos de Kubernetes cubiertos en este proyecto

- `Deployment` vs `StatefulSet` (identidad estable, almacenamiento persistente).
- `DaemonSet` (un Pod por nodo).
- `Helm` como gestor de paquetes de Kubernetes.
- Service discovery basado en anotaciones de Pod para Prometheus.
- `RBAC`: `Role`/`RoleBinding` (por namespace) vs `ClusterRole`/`ClusterRoleBinding`
  (todo el cluster).
