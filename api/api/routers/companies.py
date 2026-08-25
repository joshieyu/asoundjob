from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from scraper.models import Company, Job
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.database import get_db
from api.query import (
    companies_with_counts,
    page_envelope,
    paginate_params,
)
from api.schemas import CompanyDetail, CompanyResponse, JobSummary, PaginatedCompanies

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=PaginatedCompanies)
def list_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    verified_only: bool = False,
    db: Session = Depends(get_db),
):
    safe_page, safe_per = paginate_params(page, per_page)
    stmt = select(Company)
    if category:
        stmt = stmt.where(Company.category == category)
    if verified_only:
        stmt = stmt.where(Company.verified.is_(True))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            Company.name.ilike(pattern) | Company.description.ilike(pattern)
        )
    items, total = companies_with_counts(db, stmt, safe_page, safe_per)
    return page_envelope(items, total, safe_page, safe_per)


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
            .where(Job.company_id == company.id, Job.is_active.is_(True))
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
                    Job.company_id == company.id, Job.is_active.is_(True)
                )
            ).scalar_one()
        )
    data["active_jobs_count"] = active_count
    data["jobs"] = [JobSummary.model_validate(job) for job in jobs]
    return CompanyDetail(**data)
