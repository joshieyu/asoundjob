from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CompanyBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    logo_url: Optional[str] = None


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    location: Optional[str] = None
    country: Optional[str] = None
    country_name: Optional[str] = None
    remote: bool
    job_type: Optional[str] = None
    seniority: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    job_categories: list[str] = []
    posted_date: Optional[date] = None
    scraped_at: datetime
    expires_date: Optional[date] = None
    is_active: bool
    source: str
    company: Optional[CompanyBrief] = None


class JobDetail(JobSummary):
    description: Optional[str] = None


class PaginatedJobs(BaseModel):
    items: list[JobSummary]
    total: int
    page: int
    per_page: int
    pages: int


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    category: str
    careers_url: Optional[str] = None
    website_url: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    headquarters: Optional[str] = None
    founded: Optional[int] = None
    verified: bool
    source: str
    created_at: datetime
    active_jobs_count: int = 0


class PaginatedCompanies(BaseModel):
    items: list[CompanyResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CompanyDetail(CompanyResponse):
    jobs: list[JobSummary] = []


class CategoryInfo(BaseModel):
    id: str
    name: str
    description: str
    job_count: int


class CountryInfo(BaseModel):
    code: str
    name: str
    job_count: int


class CountriesResponse(BaseModel):
    countries: list[CountryInfo]
    unknown_count: int


class CategoriesResponse(BaseModel):
    categories: list[CategoryInfo]


class ResourceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    summary: Optional[str] = None
    category: str
    sort_order: int
    read_time: Optional[int] = None
    published: bool


class ResourceDetail(ResourceSummary):
    body: str
    created_at: datetime
    updated_at: datetime


class PaginatedResources(BaseModel):
    items: list[ResourceSummary]
    total: int
    page: int
    per_page: int
    pages: int


class JobSubmissionRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=8, max_length=1000)
    description: str = Field(min_length=20, max_length=20000)
    location: Optional[str] = Field(default=None, max_length=200)
    remote: bool = False
    job_type: Optional[str] = Field(default=None, max_length=50)
    salary_range: Optional[str] = Field(default=None, max_length=100)
    experience_level: Optional[str] = Field(default=None, max_length=50)
    audio_domain: Optional[str] = Field(default=None, max_length=50)
    submitter_name: Optional[str] = Field(default=None, max_length=200)
    submitter_email: Optional[str] = Field(default=None, max_length=320)

    @field_validator("submitter_email")
    @classmethod
    def email_must_be_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not EMAIL_RE.match(value):
            raise ValueError("invalid email address")
        return value

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, value: str) -> str:
        if not re.match(r"^https?://", value.strip()):
            raise ValueError("url must start with http:// or https://")
        return value.strip()


class SubmissionCreateResponse(BaseModel):
    id: int
    status: str
    message: str


class AdminCompanyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    careers_url: Optional[str] = Field(default=None, max_length=1000)
    website_url: Optional[str] = Field(default=None, max_length=1000)
    verified: Optional[bool] = None
    scrape_method: Optional[str] = None
    audio_scope: Optional[str] = Field(default=None, pattern="^(native|partial|all)$")
    logo_url: Optional[str] = None
    description: Optional[str] = None
    headquarters: Optional[str] = None
    founded: Optional[int] = None


class AdminCompanyCreate(AdminCompanyUpdate):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)


class RejectRequest(BaseModel):
    reason: str = Field(default="", max_length=1000)


class AdminSubmission(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    company_id: Optional[int] = None
    title: str
    description: str
    url: str
    location: Optional[str] = None
    remote: bool
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    experience_level: Optional[str] = None
    audio_domain: Optional[str] = None
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reject_reason: Optional[str] = None


JOB_FEEDBACK_KINDS = ("wrong_category", "not_audio", "broken_description", "broken_link")
SITE_FEEDBACK_KINDS = ("company_suggestion", "general")


class JobFeedbackRequest(BaseModel):
    kind: str = Field(pattern="^(wrong_category|not_audio|broken_description|broken_link)$")
    suggested_categories: Optional[list[str]] = None
    comment: Optional[str] = Field(default=None, max_length=2000)
    submitter_email: Optional[str] = Field(default=None, max_length=320)

    @field_validator("submitter_email")
    @classmethod
    def email_must_be_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not EMAIL_RE.match(value):
            raise ValueError("invalid email address")
        return value

    @model_validator(mode="after")
    def wrong_category_needs_detail(self) -> JobFeedbackRequest:
        if self.kind == "wrong_category" and not self.suggested_categories and not self.comment:
            raise ValueError(
                "wrong_category feedback requires suggested_categories or comment"
            )
        return self


class SiteFeedbackRequest(BaseModel):
    kind: str = Field(pattern="^(company_suggestion|general)$")
    company_name: Optional[str] = Field(default=None, max_length=200)
    company_url: Optional[str] = Field(default=None, max_length=1000)
    comment: Optional[str] = Field(default=None, max_length=4000)
    submitter_email: Optional[str] = Field(default=None, max_length=320)
    page_path: Optional[str] = Field(default=None, max_length=300)

    @field_validator("submitter_email")
    @classmethod
    def email_must_be_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not EMAIL_RE.match(value):
            raise ValueError("invalid email address")
        return value

    @field_validator("company_url")
    @classmethod
    def url_must_be_http(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not re.match(r"^https?://", value.strip()):
            raise ValueError("company_url must start with http:// or https://")
        return value

    @model_validator(mode="after")
    def kind_requires_fields(self) -> SiteFeedbackRequest:
        if self.kind == "company_suggestion" and not self.company_name:
            raise ValueError("company_suggestion feedback requires company_name")
        if self.kind == "general" and (not self.comment or len(self.comment) < 5):
            raise ValueError("general feedback requires a comment of at least 5 characters")
        return self


class FeedbackCreateResponse(BaseModel):
    id: int
    status: str
    message: str


class AdminJobFeedback(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    job_title: str
    company_name: Optional[str] = None
    kind: str
    suggested_categories: Optional[list[str]] = None
    comment: Optional[str] = None
    submitter_email: Optional[str] = None
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reject_reason: Optional[str] = None


class AdminSiteFeedback(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    company_name: Optional[str] = None
    company_url: Optional[str] = None
    comment: Optional[str] = None
    submitter_email: Optional[str] = None
    page_path: Optional[str] = None
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reject_reason: Optional[str] = None


class FeedbackApproveResponse(BaseModel):
    status: str
    applied: str


class ScrapeStatus(BaseModel):
    running: bool
    last_finished_at: Optional[datetime] = None
    recent: list["ScrapeLogEntry"] = []


class ScrapeLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: Optional[int] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    jobs_found: int
    error_message: Optional[str] = None
    scrape_method: Optional[str] = None


class StatsResponse(BaseModel):
    total_active_jobs: int
    audio_related_jobs: int
    total_companies: int
    verified_companies: int
    pending_submissions: int
    jobs_by_seniority: dict[str, int]
    jobs_by_category: dict[str, int]
    remote_jobs: int
    last_scrape_at: Optional[datetime] = None


ScrapeStatus.model_rebuild()
