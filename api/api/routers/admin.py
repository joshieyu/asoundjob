from __future__ import annotations

import logging
import re
import subprocess
import sys
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth import LoginRequest, TokenResponse, create_token, require_admin, verify_credentials
from api.config import COMMUNITY_JOB_TTL_DAYS, MAX_COMMUNITY_JOB_DAYS, SCRAPER_DIR
from api.database import get_db
from api.query import page_envelope, paginate_params
from api.schemas import (
    AdminCompanyCreate,
    AdminCompanyUpdate,
    AdminJobFeedback,
    AdminSiteFeedback,
    AdminSubmission,
    ApproveRequest,
    ApproveResponse,
    FeedbackApproveResponse,
    RejectRequest,
    ScrapeLogEntry,
    ScrapeStatus,
    StatsResponse,
)
from scraper.config import load_settings
from scraper.models import Company, Job, JobFeedback, JobSubmission, ScrapeLog, SiteFeedback
from scraper.normalizer import Normalizer
from scraper.overrides import effective_categories, effective_is_audio
from scraper.scrapers.base import RawJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

_scrape_lock = threading.Lock()
_scrape_process: Optional[subprocess.Popen] = None


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    if not verify_credentials(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, expires_at = create_token(payload.username)
    return TokenResponse(access_token=token, expires_at=expires_at)


@router.post("/scrape")
def trigger_scrape(
    limit: Optional[int] = Query(None, ge=1),
    _: str = Depends(require_admin),
):
    global _scrape_process
    with _scrape_lock:
        if _scrape_process is not None and _scrape_process.poll() is None:
            raise HTTPException(status_code=409, detail="Scrape already running")
        cmd = [sys.executable, "-m", "scraper.main", "--once"]
        if limit:
            cmd.extend(["--limit", str(limit)])
        _scrape_process = subprocess.Popen(
            cmd,
            cwd=str(SCRAPER_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return {"started": True, "pid": _scrape_process.pid}


@router.get("/scrape/status", response_model=ScrapeStatus)
def scrape_status(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    with _scrape_lock:
        running = _scrape_process is not None and _scrape_process.poll() is None
    recent = (
        db.execute(select(ScrapeLog).order_by(ScrapeLog.id.desc()).limit(20))
        .scalars()
        .all()
    )
    last = (
        db.execute(
            select(func.max(ScrapeLog.finished_at)).where(ScrapeLog.status == "success")
        )
    ).scalar_one_or_none()
    return ScrapeStatus(
        running=running,
        last_finished_at=last,
        recent=[ScrapeLogEntry.model_validate(entry) for entry in recent],
    )


@router.get("/scrape/log")
def scrape_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    safe_page, safe_per = paginate_params(page, per_page)
    stmt = select(ScrapeLog).order_by(ScrapeLog.id.desc())
    total = db.execute(select(func.count(ScrapeLog.id))).scalar_one()
    rows = db.execute(stmt.offset((safe_page - 1) * safe_per).limit(safe_per)).scalars().all()
    return page_envelope(
        [ScrapeLogEntry.model_validate(r) for r in rows],
        int(total),
        safe_page,
        safe_per,
    )


@router.get("/companies")
def admin_list_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    verified: Optional[bool] = None,
    sort: str = Query("name", pattern="^(name|jobs|verified)$"),
    direction: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    from api.query import companies_with_counts

    safe_page, safe_per = paginate_params(page, per_page)
    stmt = select(Company)
    if verified is not None:
        stmt = stmt.where(Company.verified.is_(verified))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Company.name.ilike(pattern))
    items, total = companies_with_counts(
        db, stmt, safe_page, safe_per, sort=sort, direction=direction
    )
    return page_envelope(items, total, safe_page, safe_per)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "company"


@router.post("/companies", status_code=201)
def admin_create_company(
    payload: AdminCompanyCreate,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    existing = db.execute(
        select(Company).where(func.lower(Company.name) == payload.name.strip().lower())
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Company already exists")

    base_slug = _slugify(payload.name)
    slug = base_slug
    suffix = 2
    while db.execute(select(Company.id).where(Company.slug == slug)).scalar_one_or_none():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    company = Company(
        name=payload.name.strip(),
        slug=slug,
        category=payload.category,
        careers_url=payload.careers_url,
        website_url=payload.website_url,
        verified=bool(payload.verified),
        source="manual",
        scrape_method=payload.scrape_method or "http",
        logo_url=payload.logo_url,
        description=payload.description,
        headquarters=payload.headquarters,
        founded=payload.founded,
    )
    db.add(company)
    db.flush()
    logger.info("admin=%s created company %s", admin, company.slug)
    return {"id": company.id, "slug": company.slug}


@router.put("/companies/{company_id}")
def admin_update_company(
    company_id: int,
    payload: AdminCompanyUpdate,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    updates.pop("name", None)
    scope_changed = "audio_scope" in updates and updates["audio_scope"] != company.audio_scope
    for field, value in updates.items():
        setattr(company, field, value)
    if updates.get("verified") or updates.get("careers_url") or scope_changed:
        company.source = "manual"
    if scope_changed:
        rescore_company_jobs(db, company)
    db.flush()
    logger.info("admin=%s updated company %s: %s", admin, company.slug, list(updates.keys()))
    return {"id": company.id, "updated_fields": sorted(updates.keys())}


def rescore_company_jobs(db: Session, company: Company) -> None:
    normalizer_settings = load_settings()
    scorer = Normalizer(normalizer_settings)
    jobs = (
        db.execute(select(Job).where(Job.company_id == company.id, Job.source == "scraper"))
        .scalars()
        .all()
    )
    for job in jobs:
        raw = RawJob(
            title=job.title,
            url=job.url,
            location=job.location,
            description=job.description,
            job_type=job.job_type,
        )
        normalized = scorer.normalize(
            raw,
            audio_scope=company.audio_scope or "native",
            company_category=company.category,
        )
        job.relevance_score = normalized.relevance_score
        job.is_audio_related = effective_is_audio(job, normalized.is_audio_related)


@router.get("/submissions")
def admin_list_submissions(
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    safe_page, safe_per = paginate_params(page, per_page)
    stmt = select(JobSubmission).order_by(JobSubmission.submitted_at.desc())
    if status != "all":
        stmt = stmt.where(JobSubmission.status == status)
    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    rows = (
        db.execute(stmt.offset((safe_page - 1) * safe_per).limit(safe_per))
        .scalars()
        .all()
    )
    return page_envelope(
        [AdminSubmission.model_validate(r) for r in rows],
        int(total),
        safe_page,
        safe_per,
    )


def find_live_community_job(db: Session, submission: JobSubmission) -> Optional[Job]:
    url = submission.url.strip().lower()
    stmt = select(Job).where(
        Job.source == "community",
        Job.is_active.is_(True),
        func.lower(Job.url) == url,
    )
    if submission.company_id is not None:
        stmt = stmt.where(Job.company_id == submission.company_id)
    else:
        stmt = stmt.where(Job.company_id.is_(None))
    return db.execute(stmt.order_by(Job.id)).scalars().first()


def refresh_community_job(row: Job, replacement: Job, normalized) -> None:
    row.title = replacement.title
    row.description = replacement.description
    row.location = replacement.location
    row.country = normalized.country
    row.remote = replacement.remote
    row.job_type = replacement.job_type
    row.seniority = replacement.seniority
    row.salary_min = replacement.salary_min
    row.salary_max = replacement.salary_max
    row.salary_currency = replacement.salary_currency
    row.job_categories = effective_categories(row, normalized.job_categories)
    row.relevance_score = normalized.relevance_score
    row.is_audio_related = effective_is_audio(row, normalized.is_audio_related)
    row.expires_date = replacement.expires_date
    row.is_active = True


def resolve_expiry_days(
    override: Optional[int], requested: Optional[int]
) -> tuple[int, str]:
    if override is not None:
        return max(1, min(override, MAX_COMMUNITY_JOB_DAYS)), "moderator"
    if requested is not None:
        return max(1, min(requested, MAX_COMMUNITY_JOB_DAYS)), "submitter"
    return COMMUNITY_JOB_TTL_DAYS, "default"


@router.post("/submissions/{submission_id}/approve", response_model=ApproveResponse)
def approve_submission(
    submission_id: int,
    payload: Optional[ApproveRequest] = None,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    submission = db.get(JobSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Submission already {submission.status}"
        )

    expires_days, expires_source = resolve_expiry_days(
        payload.expires_days if payload is not None else None,
        submission.requested_days,
    )
    expires_date = date.today() + timedelta(days=expires_days)

    normalizer = Normalizer(load_settings())
    raw = RawJob(
        title=submission.title,
        url=submission.url,
        location=submission.location,
        description=submission.description,
        job_type=submission.job_type,
        remote_hint=submission.remote,
    )

    scope = "native"
    company_category: str | None = None
    if submission.company_id is not None:
        company = db.get(Company, submission.company_id)
        if company is not None:
            if company.audio_scope:
                scope = company.audio_scope
            company_category = company.category
    normalized = normalizer.normalize(
        raw, audio_scope=scope, company_category=company_category
    )

    job = Job(
        company_id=submission.company_id,
        title=submission.title,
        description=submission.description,
        url=submission.url,
        location=normalized.location,
        country=normalized.country,
        remote=submission.remote or normalized.remote,
        job_type=normalized.job_type or submission.job_type,
        seniority=normalized.seniority,
        salary_min=normalized.salary_min,
        salary_max=normalized.salary_max,
        salary_currency=normalized.salary_currency,
        job_categories=normalized.job_categories,
        relevance_score=normalized.relevance_score,
        is_audio_related=normalized.is_audio_related,
        expires_date=expires_date,
        is_active=True,
        external_id=None,
        source="community",
    )

    duplicate = find_live_community_job(db, submission)

    now = datetime.now(timezone.utc)
    submission.status = "approved"
    submission.reviewed_at = now
    submission.reviewed_by = admin
    if duplicate is not None:
        refresh_community_job(duplicate, job, normalized)
        logger.info(
            "admin=%s approved submission %s; refreshed live job %s in place",
            admin,
            submission_id,
            duplicate.id,
        )
    else:
        db.add(job)

    db.flush()
    job_id = duplicate.id if duplicate is not None else job.id
    logger.info(
        "admin=%s approved submission %s as job %s, expires %s (%s, %d days)",
        admin,
        submission_id,
        job_id,
        expires_date,
        expires_source,
        expires_days,
    )
    return ApproveResponse(
        status="approved",
        job_id=job_id,
        expires_date=expires_date,
        expires_days=expires_days,
        expires_source=expires_source,
    )


@router.post("/submissions/{submission_id}/reject")
def reject_submission(
    submission_id: int,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    submission = db.get(JobSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Submission already {submission.status}"
        )
    now = datetime.now(timezone.utc)
    submission.status = "rejected"
    submission.reviewed_at = now
    submission.reviewed_by = admin
    submission.reject_reason = payload.reason or None
    db.flush()
    logger.info("admin=%s rejected submission %s", admin, submission_id)
    return {"status": "rejected"}


@router.get("/job-feedback")
def admin_list_job_feedback(
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    safe_page, safe_per = paginate_params(page, per_page)
    stmt = (
        select(JobFeedback, Job.title, Company.name)
        .join(Job, JobFeedback.job_id == Job.id)
        .outerjoin(Company, Job.company_id == Company.id)
        .order_by(JobFeedback.submitted_at.desc())
    )
    if status != "all":
        stmt = stmt.where(JobFeedback.status == status)
    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    rows = db.execute(stmt.offset((safe_page - 1) * safe_per).limit(safe_per)).all()
    items = []
    for feedback, job_title, company_name in rows:
        data = {
            column.name: getattr(feedback, column.name)
            for column in JobFeedback.__table__.columns
        }
        data["job_title"] = job_title
        data["company_name"] = company_name
        items.append(AdminJobFeedback.model_validate(data))
    return page_envelope(items, int(total), safe_page, safe_per)


@router.post("/job-feedback/{feedback_id}/approve", response_model=FeedbackApproveResponse)
def approve_job_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    feedback = db.get(JobFeedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    if feedback.status != "pending":
        raise HTTPException(status_code=409, detail=f"Feedback already {feedback.status}")

    job = db.get(Job, feedback.job_id)
    applied = "no changes"
    if feedback.kind == "not_audio":
        if job is not None:
            job.is_audio_related_override = False
            job.is_audio_related = False
        applied = "marked not audio-related"
    elif feedback.kind == "wrong_category":
        if job is not None and feedback.suggested_categories:
            job.categories_override = feedback.suggested_categories
            job.job_categories = feedback.suggested_categories
            applied = f"categories set to {', '.join(feedback.suggested_categories)}"
        else:
            applied = "no categories suggested"
    elif feedback.kind in ("broken_description", "broken_link"):
        applied = "marked handled, no job changes"

    now = datetime.now(timezone.utc)
    feedback.status = "approved"
    feedback.reviewed_at = now
    feedback.reviewed_by = admin
    db.flush()
    logger.info("admin=%s approved job feedback %s: %s", admin, feedback_id, applied)
    return FeedbackApproveResponse(status="approved", applied=applied)


@router.post("/job-feedback/{feedback_id}/reject")
def reject_job_feedback(
    feedback_id: int,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    feedback = db.get(JobFeedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    if feedback.status != "pending":
        raise HTTPException(status_code=409, detail=f"Feedback already {feedback.status}")
    now = datetime.now(timezone.utc)
    feedback.status = "rejected"
    feedback.reviewed_at = now
    feedback.reviewed_by = admin
    feedback.reject_reason = payload.reason or None
    db.flush()
    logger.info("admin=%s rejected job feedback %s", admin, feedback_id)
    return {"status": "rejected"}


@router.get("/site-feedback")
def admin_list_site_feedback(
    status: str = Query("pending", pattern="^(pending|approved|rejected|all)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    safe_page, safe_per = paginate_params(page, per_page)
    stmt = select(SiteFeedback).order_by(SiteFeedback.submitted_at.desc())
    if status != "all":
        stmt = stmt.where(SiteFeedback.status == status)
    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    rows = (
        db.execute(stmt.offset((safe_page - 1) * safe_per).limit(safe_per))
        .scalars()
        .all()
    )
    return page_envelope(
        [AdminSiteFeedback.model_validate(r) for r in rows],
        int(total),
        safe_page,
        safe_per,
    )


@router.post("/site-feedback/{feedback_id}/resolve")
def resolve_site_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    feedback = db.get(SiteFeedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    if feedback.status != "pending":
        raise HTTPException(status_code=409, detail=f"Feedback already {feedback.status}")
    now = datetime.now(timezone.utc)
    feedback.status = "approved"
    feedback.reviewed_at = now
    feedback.reviewed_by = admin
    db.flush()
    logger.info("admin=%s resolved site feedback %s", admin, feedback_id)
    return {"status": "approved"}


@router.post("/site-feedback/{feedback_id}/reject")
def reject_site_feedback(
    feedback_id: int,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    admin: str = Depends(require_admin),
):
    feedback = db.get(SiteFeedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    if feedback.status != "pending":
        raise HTTPException(status_code=409, detail=f"Feedback already {feedback.status}")
    now = datetime.now(timezone.utc)
    feedback.status = "rejected"
    feedback.reviewed_at = now
    feedback.reviewed_by = admin
    feedback.reject_reason = payload.reason or None
    db.flush()
    logger.info("admin=%s rejected site feedback %s", admin, feedback_id)
    return {"status": "rejected"}


@router.get("/stats", response_model=StatsResponse)
def admin_stats(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    total_jobs = db.execute(
        select(func.count(Job.id)).where(Job.is_active.is_(True))
    ).scalar_one()
    related_jobs = db.execute(
        select(func.count(Job.id)).where(
            Job.is_active.is_(True), Job.is_audio_related.is_(True)
        )
    ).scalar_one()
    total_companies = db.execute(select(func.count(Company.id))).scalar_one()
    verified = db.execute(
        select(func.count(Company.id)).where(Company.verified.is_(True))
    ).scalar_one()
    pending = db.execute(
        select(func.count(JobSubmission.id)).where(JobSubmission.status == "pending")
    ).scalar_one()
    remote = db.execute(
        select(func.count(Job.id)).where(Job.remote.is_(True), Job.is_active.is_(True))
    ).scalar_one()

    by_seniority_rows = db.execute(
        select(Job.seniority, func.count(Job.id))
        .where(Job.is_active.is_(True))
        .group_by(Job.seniority)
    ).all()
    by_seniority = {
        (row[0] or "unknown"): int(row[1]) for row in by_seniority_rows
    }

    counts: dict[str, int] = {}
    cat_rows = db.execute(
        select(Job.job_categories).where(Job.is_active.is_(True))
    ).all()
    for (cats,) in cat_rows:
        for cat in cats or []:
            counts[cat] = counts.get(cat, 0) + 1

    last_scrape = db.execute(
        select(func.max(ScrapeLog.started_at))
    ).scalar_one_or_none()

    return StatsResponse(
        total_active_jobs=int(total_jobs),
        audio_related_jobs=int(related_jobs),
        total_companies=int(total_companies),
        verified_companies=int(verified),
        pending_submissions=int(pending),
        jobs_by_seniority=by_seniority,
        jobs_by_category=counts,
        remote_jobs=int(remote),
        last_scrape_at=last_scrape,
    )
