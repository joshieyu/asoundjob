from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import CORS_ORIGINS
from api.database import init_db
from api.routers import (
    admin,
    categories,
    companies,
    countries,
    feedback,
    jobs,
    resources,
    search,
)

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ASoundJob API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(companies.router)
app.include_router(categories.router)
app.include_router(countries.router)
app.include_router(search.router)
app.include_router(resources.router)
app.include_router(feedback.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
