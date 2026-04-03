from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.api.routes import health, trains, history, stations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB schema already initialized via seed script / collector
    yield


app = FastAPI(title="Train Punctuality Service", version="0.1.0", lifespan=lifespan)

app.include_router(health.router, prefix="/api/v1")
app.include_router(trains.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(stations.router, prefix="/api/v1")
