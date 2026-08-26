from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from scraper.models import Company, Job, JobSubmission
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.query import apply_job_filters, fetch_job_page, page_envelope, paginate_params
from api.rate_limit import SubmissionRateLimiter
from api.schemas import (
    JobDetail,
    JobSubmissionRequest,
    JobSummary,
    PaginatedJobs,
    SubmissionCreateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

rate_limiter = SubmissionRateLimiter()


def _parse_csv(value: Optional[str]) -> Optional[list[str]]:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


@router.get("", response_model=PaginatedJobs)
def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    category: Optional[str] = None,
    seniority: Optional[str] = None,
    job_type: Optional[str] = None,
    salary_min: Optional[int] = Query(None, ge=0),
    salary_max: Optional[int] = Query(None, ge=0),
    company_id: Optional[int] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    include_unrelated: bool = False,
    search: Optional[str] = None,
    sort: str = Query("newest", pattern="^(newest|oldest|salary_desc|salary_asc)$"),
    db: Session = Depends(get_db),
):
    safe_page, safe_per = paginate_params(page, per_page)
    stmt = apply_job_filters(
        select(Job),
        category=_parse_csv(category),
        seniority=seniority,
        job_type=job_type,
        salary_min=salary_min,
        salary_max=salary_max,
        company_id=company_id,
        location=location,
        remote=remote,
        search=search,
        include_unrelated=include_unrelated,
    )
    jobs, total = fetch_job_page(db, stmt, safe_page, safe_per, sort)
    return page_envelope(
        [JobSummary.model_validate(job) for job in jobs], total, safe_page, safe_per
    )


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobDetail.model_validate(job)


@router.post("/submit", response_model=SubmissionCreateResponse, status_code=201)
def submit_job(
    request: Request,
    payload: JobSubmissionRequest,
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many submissions. Try again later ({retry_after}).",
        )

    company = db.execute(
        select(Company).where(func.lower(Company.name) == payload.company_name.strip().lower())
    ).scalar_one_or_none()

    submission = JobSubmission(
        company_name=payload.company_name.strip(),
        company_id=company.id if company else None,
        title=payload.title.strip(),
        description=payload.description,
        url=payload.url,
        location=payload.location,
        remote=payload.remote,
        job_type=payload.job_type,
        salary_range=payload.salary_range,
        experience_level=payload.experience_level,
        audio_domain=payload.audio_domain,
        submitter_name=payload.submitter_name,
        submitter_email=payload.submitter_email,
        status="pending",
    )
    db.add(submission)
    db.flush()
    return SubmissionCreateResponse(
        id=submission.id,
        status=submission.status,
        message="Submission received and pending review",
    )
