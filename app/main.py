from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
import time, random


app = FastAPI(title="PulseBoard API")

#Instrumentar automáticamente - expone /metrics con formato Prometheus
Instrumentator().instrument(app).expose(app)

@app.get("/")
def root():
    return{"status": "ok", "service": "pulseboard-api"}

@app.get("/items/{item_id}")
def get_item(item_id: int):
    #Simular latencia variable para que se note en Grafana.
    time.sleep(random.uniform(0.01, 0.3))
    return{"id": item_id, "name": f"item-{item_id}"}

@app.get("/health")
def health():
    return{"healthy": True}

