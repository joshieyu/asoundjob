from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from scraper.models import CareerResource
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.query import page_envelope, paginate_params
from api.schemas import PaginatedResources, ResourceDetail, ResourceSummary

router = APIRouter(prefix="/api/resources", tags=["resources"])


@router.get("", response_model=PaginatedResources)
def list_resources(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    safe_page, safe_per = paginate_params(page, per_page)
    stmt = select(CareerResource).where(CareerResource.published.is_(True))
    if category:
        stmt = stmt.where(CareerResource.category == category)
    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    rows = (
        db.execute(
            stmt.order_by(CareerResource.sort_order, CareerResource.title)
            .offset((safe_page - 1) * safe_per)
            .limit(safe_per)
        )
        .scalars()
        .all()
    )
    return page_envelope(
        [ResourceSummary.model_validate(r) for r in rows], int(total), safe_page, safe_per
    )


@router.get("/interview-prep", response_model=PaginatedResources)
def list_interview_prep(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list_resources(page=page, per_page=per_page, category="interview-prep", db=db)


@router.get("/{slug}", response_model=ResourceDetail)
def get_resource(slug: str, db: Session = Depends(get_db)):
    resource = db.execute(
        select(CareerResource).where(
            CareerResource.slug == slug, CareerResource.published.is_(True)
        )
    ).scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return ResourceDetail.model_validate(resource)
