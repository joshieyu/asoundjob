from __future__ import annotations

from scraper.models import Job


def effective_categories(job: Job, computed: list[str]) -> list[str]:
    if job.categories_override is not None:
        return list(job.categories_override)
    return computed


def effective_is_audio(job: Job, computed: bool) -> bool:
    if job.is_audio_related_override is not None:
        return bool(job.is_audio_related_override)
    return computed
