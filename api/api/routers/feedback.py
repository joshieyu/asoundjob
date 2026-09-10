from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.database import get_db
from api.rate_limit import SubmissionRateLimiter
from api.routers.categories import load_categories
from api.schemas import (
    FeedbackCreateResponse,
    JobFeedbackRequest,
    SiteFeedbackRequest,
)
from scraper.models import Job, JobFeedback, SiteFeedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["feedback"])

feedback_rate_limiter = SubmissionRateLimiter(max_per_day=20)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _enforce_rate_limit(request: Request) -> None:
    allowed, retry_after = feedback_rate_limiter.check(_client_ip(request))
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many submissions. Try again later ({retry_after}).",
        )


@router.post(
    "/jobs/{job_id}/feedback", response_model=FeedbackCreateResponse, status_code=201
)
def submit_job_feedback(
    job_id: int,
    payload: JobFeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _enforce_rate_limit(request)

    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if payload.suggested_categories:
        known_ids = {category["id"] for category in load_categories()}
        unknown = [cat for cat in payload.suggested_categories if cat not in known_ids]
        if unknown:
            raise HTTPException(
                status_code=422, detail=f"Unknown category ids: {', '.join(unknown)}"
            )

    feedback = JobFeedback(
        job_id=job_id,
        kind=payload.kind,
        suggested_categories=payload.suggested_categories,
        comment=payload.comment,
        submitter_email=payload.submitter_email,
        status="pending",
    )
    db.add(feedback)
    db.flush()
    return FeedbackCreateResponse(
        id=feedback.id,
        status=feedback.status,
        message="Feedback received and pending review",
    )


@router.post("/feedback", response_model=FeedbackCreateResponse, status_code=201)
def submit_site_feedback(
    payload: SiteFeedbackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _enforce_rate_limit(request)

    feedback = SiteFeedback(
        kind=payload.kind,
        company_name=payload.company_name,
        company_url=payload.company_url,
        comment=payload.comment,
        submitter_email=payload.submitter_email,
        page_path=payload.page_path,
        status="pending",
    )
    db.add(feedback)
    db.flush()
    return FeedbackCreateResponse(
        id=feedback.id,
        status=feedback.status,
        message="Feedback received and pending review",
    )
