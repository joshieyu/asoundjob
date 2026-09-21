from __future__ import annotations

from typing import Optional, Union

from sqlalchemy import String, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from api.config import MAX_PER_PAGE
from scraper.company_health import (
    GRADE_ORDER,
    grade_company,
    grade_rank,
    in_scrape_population,
    is_described,
    shape_shares,
)
from scraper.models import Company, Job, ScrapeLog
from scraper.url_shape import URL_SHAPES, classify_careers_url


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


COMPANY_HEALTH_SORTS = ("grade", "board", "active", "name")


def _scrape_log_summary(session: Session) -> dict:
    rows = session.execute(
        select(ScrapeLog.company_id, ScrapeLog.status, ScrapeLog.started_at, ScrapeLog.jobs_found)
        .where(ScrapeLog.company_id.is_not(None))
        .order_by(ScrapeLog.company_id, ScrapeLog.started_at.desc(), ScrapeLog.id.desc())
    ).all()
    summary: dict = {}
    still_counting: dict = {}
    for company_id, status, started_at, jobs_found in rows:
        entry = summary.get(company_id)
        if entry is None:
            entry = {
                "last_scrape_status": status,
                "last_scrape_at": started_at,
                "last_jobs_found": int(jobs_found or 0),
                "consecutive_failures": 0,
            }
            summary[company_id] = entry
            still_counting[company_id] = True
        if still_counting.get(company_id):
            if status == "failed":
                entry["consecutive_failures"] += 1
            else:
                still_counting[company_id] = False
    return summary


def _job_health_summary(session: Session) -> dict:
    rows = session.execute(
        select(Job.company_id, Job.title, Job.description, Job.is_audio_related).where(
            Job.is_active.is_(True)
        )
    ).all()
    summary: dict = {}
    for company_id, title, description, is_audio_related in rows:
        if company_id is None:
            continue
        entry = summary.setdefault(
            company_id,
            {"titles": [], "described_flags": [], "board_count": 0},
        )
        entry["titles"].append(title)
        entry["described_flags"].append(is_described(description))
        if is_audio_related:
            entry["board_count"] += 1
    return summary


def company_health_rows(session: Session, q: Optional[str] = None) -> list:
    stmt = select(
        Company.id,
        Company.name,
        Company.slug,
        Company.category,
        Company.verified,
        Company.careers_url,
        Company.scrape_blocked,
    )
    if q and q.strip():
        stmt = stmt.where(Company.name.ilike(f"%{q.strip()}%"))
    companies = session.execute(stmt.order_by(Company.name)).all()

    scrape_summary = _scrape_log_summary(session)
    job_summary = _job_health_summary(session)
    empty_jobs = {"titles": [], "described_flags": [], "board_count": 0}

    rows = []
    for company_id, name, slug, category, verified, careers_url, scrape_blocked in companies:
        scrape = scrape_summary.get(company_id)
        jobs = job_summary.get(company_id, empty_jobs)
        titles = jobs["titles"]
        active_rows = len(titles)
        described_share, role_share = shape_shares(titles, jobs["described_flags"])
        board_count = jobs["board_count"]
        last_scrape_status = scrape["last_scrape_status"] if scrape else None
        scraped = in_scrape_population(verified, careers_url, scrape_blocked)
        grade = grade_company(
            active_rows,
            described_share,
            role_share,
            board_count,
            last_scrape_status,
            scraped=scraped,
        )
        rows.append(
            {
                "company_id": company_id,
                "name": name,
                "slug": slug,
                "category": category,
                "verified": bool(verified),
                "careers_url": careers_url,
                "last_scrape_status": last_scrape_status,
                "last_scrape_at": scrape["last_scrape_at"] if scrape else None,
                "last_jobs_found": scrape["last_jobs_found"] if scrape else None,
                "consecutive_failures": scrape["consecutive_failures"] if scrape else 0,
                "active_rows": active_rows,
                "described_share": described_share,
                "role_share": role_share,
                "board_count": board_count,
                "grade": grade,
                "scraped": scraped,
                "url_shape": classify_careers_url(careers_url),
            }
        )
    return rows


def company_health_page(
    session: Session,
    grade: Optional[str] = None,
    url_shape: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    sort: str = "grade",
    direction: str = "desc",
):
    rows = company_health_rows(session, q=q)
    filtered = [r for r in rows if r["grade"] == grade] if grade in GRADE_ORDER else rows
    if url_shape in URL_SHAPES:
        filtered = [r for r in filtered if r["url_shape"] == url_shape]

    summary = {g: 0 for g in GRADE_ORDER}
    for row in filtered:
        summary[row["grade"]] += 1

    if sort not in COMPANY_HEALTH_SORTS:
        sort = "grade"
    if direction not in SORT_DIRECTIONS:
        direction = "desc"
    descending = direction == "desc"

    rows_sorted = sorted(filtered, key=lambda r: r["name"])
    if sort == "board":
        rows_sorted.sort(key=lambda r: r["board_count"], reverse=descending)
    elif sort == "active":
        rows_sorted.sort(key=lambda r: r["active_rows"], reverse=descending)
    elif sort == "name":
        rows_sorted.sort(key=lambda r: r["name"], reverse=descending)
    else:
        rows_sorted.sort(key=lambda r: grade_rank(r["grade"]), reverse=not descending)

    total = len(rows_sorted)
    safe_page = max(1, page)
    start = (safe_page - 1) * per_page
    page_rows = rows_sorted[start : start + per_page]
    return page_rows, total, summary
