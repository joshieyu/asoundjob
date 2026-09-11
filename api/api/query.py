from __future__ import annotations

from typing import Optional, Union

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


def _as_list(value: Union[str, list[str], None]) -> Optional[list[str]]:
    """Accept a single value or a list, and return a lowercased list.

    Callers predate multi-select and still pass plain strings (see
    routers/search.py), so both shapes stay valid.
    """
    if value is None:
        return None
    values = [value] if isinstance(value, str) else list(value)
    cleaned = [v.strip().lower() for v in values if v and v.strip()]
    return cleaned or None


def apply_job_filters(
    stmt,
    category: Optional[list[str]] = None,
    seniority: Union[str, list[str], None] = None,
    job_type: Union[str, list[str], None] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    company_id: Optional[int] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    country: Optional[str] = None,
    remote: Optional[bool] = None,
    search: Optional[str] = None,
    include_unrelated: bool = False,
    ids: Optional[list[int]] = None,
):
    stmt = stmt.where(Job.is_active.is_(True))
    if ids is not None:
        stmt = stmt.where(Job.id.in_(ids))
    if not include_unrelated:
        stmt = stmt.where(Job.is_audio_related.is_(True))
    seniorities = _as_list(seniority)
    if seniorities:
        stmt = stmt.where(Job.seniority.in_(seniorities))
    job_types = _as_list(job_type)
    if job_types:
        stmt = stmt.where(Job.job_type.in_(job_types))
    if company_id is not None:
        stmt = stmt.where(Job.company_id == company_id)
    if company and company.strip():
        stmt = stmt.where(Job.company.has(Company.name.ilike(f"%{company.strip()}%")))
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


COMPANY_SORTS = ("name", "jobs", "board", "verified")
SORT_DIRECTIONS = ("asc", "desc")


def companies_with_counts(
    session: Session,
    base_stmt,
    page: int,
    per_page: int,
    sort: str = "name",
    direction: str = "asc",
):
    counts_subq = (
        select(
            Job.company_id,
            func.count(Job.id).label("job_count"),
            func.sum(case((Job.is_audio_related.is_(True), 1), else_=0)).label(
                "board_count"
            ),
        )
        .where(Job.is_active.is_(True))
        .group_by(Job.company_id)
        .subquery()
    )
    job_count = func.coalesce(counts_subq.c.job_count, 0)
    board_count = func.coalesce(counts_subq.c.board_count, 0)
    if sort not in COMPANY_SORTS:
        sort = "name"
    if direction not in SORT_DIRECTIONS:
        direction = "asc"
    descending = direction == "desc"
    if sort == "jobs":
        order_by = [
            job_count.desc() if descending else job_count.asc(),
            Company.name.asc(),
        ]
    elif sort == "board":
        order_by = [
            board_count.desc() if descending else board_count.asc(),
            Company.name.asc(),
        ]
    elif sort == "verified":
        order_by = [
            Company.verified.desc() if descending else Company.verified.asc(),
            Company.name.asc(),
        ]
    else:
        order_by = [Company.name.desc() if descending else Company.name.asc()]
    total = session.execute(
        select(func.count()).select_from(base_stmt.subquery())
    ).scalar_one()
    rows = session.execute(
        base_stmt.add_columns(
            job_count.label("job_count"), board_count.label("board_count")
        )
        .outerjoin(counts_subq, counts_subq.c.company_id == Company.id)
        .order_by(*order_by)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()

    items = []
    for row in rows:
        company = row[0]
        data = {c.name: getattr(company, c.name) for c in Company.__table__.columns}
        data["active_jobs_count"] = int(row[-2])
        data["board_jobs_count"] = int(row[-1])
        items.append(data)
    return items, int(total)
