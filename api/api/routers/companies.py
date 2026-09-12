from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from api.database import get_db
from api.query import (
    companies_with_counts,
    page_envelope,
    paginate_params,
)
from api.rate_limit import SubmissionRateLimiter
from api.schemas import (
    BlockedCompaniesResponse,
    BlockedCompany,
    CompanyCategoriesResponse,
    CompanyCategoryInfo,
    CompanyDetail,
    CompanyResponse,
    CompanySuggestionRequest,
    FeedbackCreateResponse,
    JobSummary,
    OpenApplicationCompany,
    OpenApplicationsResponse,
    PaginatedCompanies,
)
from scraper.models import Company, CompanySuggestion, Job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/companies", tags=["companies"])

suggestion_rate_limiter = SubmissionRateLimiter(max_per_day=20)


@router.get("", response_model=PaginatedCompanies)
def list_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    verified_only: bool = False,
    hiring_only: bool = False,
    sort: str = Query("board", pattern="^(name|jobs|board|verified)$"),
    direction: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
):
    safe_page, safe_per = paginate_params(page, per_page)
    stmt = select(Company)
    if category:
        stmt = stmt.where(Company.category == category)
    if verified_only:
        stmt = stmt.where(Company.verified.is_(True))
    if hiring_only:
        stmt = stmt.where(_board_jobs_exist())
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            Company.name.ilike(pattern) | Company.description.ilike(pattern)
        )
    items, total = companies_with_counts(
        db, stmt, safe_page, safe_per, sort=sort, direction=direction
    )
    return page_envelope(items, total, safe_page, safe_per)


def _board_jobs_exist():
    return (
        select(Job.id)
        .where(
            Job.company_id == Company.id,
            Job.is_active.is_(True),
            Job.is_audio_related.is_(True),
        )
        .exists()
    )


@router.get("/categories", response_model=CompanyCategoriesResponse)
def list_company_categories(db: Session = Depends(get_db)):
    board_jobs = func.sum(
        case(
            (
                Job.is_active.is_(True) & Job.is_audio_related.is_(True),
                1,
            ),
            else_=0,
        )
    )
    rows = db.execute(
        select(
            Company.category,
            func.count(func.distinct(Company.id)),
            func.coalesce(board_jobs, 0),
        )
        .outerjoin(Job, Job.company_id == Company.id)
        .group_by(Company.category)
        .order_by(Company.category.asc())
    ).all()
    categories = [
        CompanyCategoryInfo(
            name=name, company_count=int(companies), board_jobs_count=int(jobs)
        )
        for name, companies, jobs in rows
    ]
    return CompanyCategoriesResponse(
        categories=categories, total=sum(c.company_count for c in categories)
    )


@router.get("/open-applications", response_model=OpenApplicationsResponse)
def list_open_applications(db: Session = Depends(get_db)):
    open_roles_subq = (
        select(
            Job.company_id,
            func.sum(case((Job.is_audio_related.is_(True), 1), else_=0)).label(
                "open_roles"
            ),
        )
        .where(Job.is_active.is_(True))
        .group_by(Job.company_id)
        .subquery()
    )
    open_roles = func.coalesce(open_roles_subq.c.open_roles, 0)
    rows = db.execute(
        select(Company, open_roles.label("open_roles"))
        .outerjoin(open_roles_subq, open_roles_subq.c.company_id == Company.id)
        .where(Company.open_application.is_(True), Company.verified.is_(True))
        .order_by(Company.name)
    ).all()
    companies = [
        OpenApplicationCompany(
            id=company_row.id,
            name=company_row.name,
            slug=company_row.slug,
            category=company_row.category,
            careers_url=company_row.careers_url,
            open_roles=int(roles),
        )
        for company_row, roles in rows
    ]
    return OpenApplicationsResponse(companies=companies, total=len(companies))


@router.get("/blocked", response_model=BlockedCompaniesResponse)
def list_blocked_companies(db: Session = Depends(get_db)):
    active_audio_job = (
        select(Job.id)
        .where(
            Job.company_id == Company.id,
            Job.is_active.is_(True),
            Job.is_audio_related.is_(True),
        )
        .exists()
    )
    rows = db.execute(
        select(Company)
        .where(
            Company.scrape_blocked.is_(True),
            ~active_audio_job,
        )
        .order_by(Company.name)
    ).scalars().all()
    companies = [BlockedCompany.model_validate(company_row) for company_row in rows]
    return BlockedCompaniesResponse(companies=companies, total=len(companies))


@router.get("/{slug}", response_model=CompanyDetail)
def get_company(slug: str, db: Session = Depends(get_db)):
    company = db.execute(
        select(Company).where(Company.slug == slug)
    ).scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    jobs = (
        db.execute(
            select(Job)
            .where(
                Job.company_id == company.id,
                Job.is_active.is_(True),
                Job.is_audio_related.is_(True),
            )
            .options(selectinload(Job.company))
            .order_by(Job.posted_date.desc().nullslast(), Job.scraped_at.desc())
            .limit(100)
        )
        .scalars()
        .all()
    )
    data = CompanyResponse.model_validate(company).model_dump()
    active_count = len(jobs)
    if active_count == 100:
        from sqlalchemy import func

        active_count = int(
            db.execute(
                select(func.count(Job.id)).where(
                    Job.company_id == company.id,
                    Job.is_active.is_(True),
                    Job.is_audio_related.is_(True),
                )
            ).scalar_one()
        )
    data["active_jobs_count"] = active_count
    data["board_jobs_count"] = active_count
    data["jobs"] = [JobSummary.model_validate(job) for job in jobs]
    return CompanyDetail(**data)


@router.post(
    "/{slug}/suggestion", response_model=FeedbackCreateResponse, status_code=201
)
def submit_company_suggestion(
    slug: str,
    payload: CompanySuggestionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    client = request.client.host if request.client else "unknown"
    allowed, retry_after = suggestion_rate_limiter.check(client)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many submissions. Try again later ({retry_after}).",
        )

    company = db.execute(
        select(Company).where(Company.slug == slug)
    ).scalar_one_or_none()
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    suggestion = CompanySuggestion(
        company_id=company.id,
        description=(payload.description or "").strip() or None,
        links=[link.model_dump() for link in payload.links] if payload.links else None,
        headquarters=(payload.headquarters or "").strip() or None,
        founded=payload.founded,
        comment=(payload.comment or "").strip() or None,
        submitter_email=(payload.submitter_email or "").strip() or None,
        status="pending",
    )
    db.add(suggestion)
    db.flush()
    logger.info("company suggestion %s submitted for %s", suggestion.id, slug)
    return FeedbackCreateResponse(
        id=suggestion.id,
        status="pending",
        message="Thanks — a moderator will review this before it appears.",
    )
