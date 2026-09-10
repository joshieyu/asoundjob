from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.database import get_db
from api.schemas import CountriesResponse, CountryInfo
from scraper.countries import country_name
from scraper.models import Job

router = APIRouter(prefix="/api/countries", tags=["countries"])


@router.get("", response_model=CountriesResponse)
def get_countries(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Job.country, func.count(Job.id))
        .where(Job.is_active.is_(True), Job.is_audio_related.is_(True))
        .group_by(Job.country)
    ).all()

    countries: list[CountryInfo] = []
    unknown = 0
    for code, count in rows:
        name = country_name(code)
        if code is None or name is None:
            unknown += count
            continue
        countries.append(CountryInfo(code=code, name=name, job_count=count))

    countries.sort(key=lambda item: (-item.job_count, item.name))
    return CountriesResponse(countries=countries, unknown_count=unknown)
