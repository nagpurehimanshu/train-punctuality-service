from fastapi import FastAPI
from src.db.database import init_db
from src.api.routes import health, trains, history, stations

app = FastAPI(title="Train Punctuality Service", version="0.1.0")

app.include_router(health.router, prefix="/api/v1")
app.include_router(trains.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(stations.router, prefix="/api/v1")


@app.on_event("startup")
def startup():
    init_db()
