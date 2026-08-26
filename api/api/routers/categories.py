from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from scraper.config import REPO_ROOT, load_settings
from scraper.models import Job
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import CategoriesResponse, CategoryInfo

router = APIRouter(prefix="/api/categories", tags=["categories"])

_CATEGORIES_FILE = REPO_ROOT / "data" / "audio_job_categories.json"


def load_categories() -> list[dict]:
    settings = load_settings()
    path = settings.data_dir / "audio_job_categories.json"
    if not path.exists():
        path = _CATEGORIES_FILE
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data["job_categories"]


@router.get("", response_model=CategoriesResponse)
def get_categories(db: Session = Depends(get_db)):
    categories = load_categories()
    counts: dict[str, int] = {}
    rows = db.execute(
        select(Job.job_categories).where(
            Job.is_active.is_(True), Job.is_audio_related.is_(True)
        )
    ).all()
    for (cats,) in rows:
        if not cats:
            continue
        for cat in cats:
            counts[cat] = counts.get(cat, 0) + 1

    items = [
        CategoryInfo(
            id=cat["id"],
            name=cat["name"],
            description=cat["description"],
            job_count=counts.get(cat["id"], 0),
        )
        for cat in categories
    ]
    return CategoriesResponse(categories=items)
