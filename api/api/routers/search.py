from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from scraper.models import Job
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.query import apply_job_filters, fetch_job_page, page_envelope, paginate_params
from api.schemas import JobSummary, PaginatedJobs

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=PaginatedJobs)
def search_jobs(
    q: str = Query(..., min_length=1, max_length=200),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    sort: str = Query("newest", pattern="^(newest|oldest|salary_desc|salary_asc)$"),
    category: Optional[str] = None,
    seniority: Optional[str] = None,
    remote: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    safe_page, safe_per = paginate_params(page, per_page)
    categories = None
    if category:
        categories = [c.strip() for c in category.split(",") if c.strip()] or None
    stmt = apply_job_filters(
        select(Job),
        category=categories,
        seniority=seniority,
        remote=remote,
        search=q,
    )
    jobs, total = fetch_job_page(db, stmt, safe_page, safe_per, sort)
    return page_envelope(
        [JobSummary.model_validate(job) for job in jobs], total, safe_page, safe_per
    )
