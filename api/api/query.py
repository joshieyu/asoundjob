from __future__ import annotations

from typing import Optional

from sqlalchemy import String, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from api.config import MAX_PER_PAGE
from scraper.models import Company, Job


def paginate_params(page: int, per_page: int) -> tuple[int, int]:
    safe_page = max(1, page)
    safe_per = min(max(1, per_page), MAX_PER_PAGE)
    return safe_page, safe_per


def page_envelope(items: list, total: int, page: int, per_page: int) -> dict:
    pages = (total + per_page - 1) // per_page if per_page else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


def apply_job_filters(
    stmt,
    category: Optional[list[str]] = None,
    seniority: Optional[str] = None,
    job_type: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    company_id: Optional[int] = None,
    location: Optional[str] = None,
    country: Optional[str] = None,
    remote: Optional[bool] = None,
    search: Optional[str] = None,
    include_unrelated: bool = False,
):
    stmt = stmt.where(Job.is_active.is_(True))
    if not include_unrelated:
        stmt = stmt.where(Job.is_audio_related.is_(True))
    if seniority:
        stmt = stmt.where(Job.seniority == seniority.lower())
    if job_type:
        stmt = stmt.where(Job.job_type == job_type.lower())
    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)
    if remote is not None:
        stmt = stmt.where(Job.remote.is_(remote))
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{location}%"))
    if country:
        stmt = stmt.where(
            or_(Job.country == country.upper(), Job.country.is_(None))
        )
    if salary_min is not None:
        stmt = stmt.where(or_(Job.salary_max.is_(None), Job.salary_max >= salary_min))
    if salary_max is not None:
        stmt = stmt.where(or_(Job.salary_min.is_(None), Job.salary_min <= salary_max))
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Job.title.ilike(pattern), Job.description.ilike(pattern)))
    if category:
        like_conds = [
            Job.job_categories.cast(String).like(f'%"{cat}"%') for cat in category
        ]
        stmt = stmt.where(or_(*like_conds))
    return stmt


SORT_OPTIONS = {
    "newest": [Job.posted_date.desc().nullslast(), Job.scraped_at.desc()],
    "oldest": [Job.posted_date.asc().nullsfirst(), Job.scraped_at.asc()],
    "salary_desc": [
        func.coalesce(Job.salary_max, Job.salary_min, 0).desc(),
        Job.posted_date.desc().nullslast(),
    ],
    "salary_asc": [
        func.coalesce(Job.salary_max, Job.salary_min, 1_000_000_000).asc(),
        Job.posted_date.desc().nullslast(),
    ],
}


def fetch_job_page(
    session: Session,
    base_stmt,
    page: int,
    per_page: int,
    sort: str = "newest",
    country_first: Optional[str] = None,
):
    order_by = list(SORT_OPTIONS.get(sort, SORT_OPTIONS["newest"]))
    if country_first:
        order_by.insert(0, case((Job.country == country_first.upper(), 0), else_=1))
    total = session.execute(
        select(func.count()).select_from(base_stmt.subquery())
    ).scalar_one()
    rows = (
        session.execute(
            base_stmt.options(selectinload(Job.company))
            .order_by(*order_by)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        .scalars()
        .all()
    )
    return list(rows), int(total)


def companies_with_counts(session: Session, base_stmt, page: int, per_page: int):
    counts_subq = (
        select(Job.company_id, func.count(Job.id).label("job_count"))
        .where(Job.is_active.is_(True))
        .group_by(Job.company_id)
        .subquery()
    )
    total = session.execute(
        select(func.count()).select_from(base_stmt.subquery())
    ).scalar_one()
    rows = session.execute(
        base_stmt.add_columns(func.coalesce(counts_subq.c.job_count, 0).label("job_count"))
        .outerjoin(counts_subq, counts_subq.c.company_id == Company.id)
        .order_by(Company.name)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    items = []
    for row in rows:
        company = row[0]
        count = row[-1]
        data = {c.name: getattr(company, c.name) for c in Company.__table__.columns}
        data["active_jobs_count"] = int(count)
        items.append(data)
    return items, int(total)
