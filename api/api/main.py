from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import seed_file
from api.config import CORS_ORIGINS, dev_credentials_in_use, production_config_errors
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
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    errors = production_config_errors(os.environ)
    if errors:
        raise RuntimeError(
            "refusing to start with ASOUNDJOB_ENV=production: " + "; ".join(errors)
        )
    if dev_credentials_in_use(os.environ):
        logger.warning(
            "API is running with development admin credentials; "
            "ASOUNDJOB_ENV=production refuses to start this way"
        )
    init_db()
    seed_file.enable()
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
