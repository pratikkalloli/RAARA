from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

VerificationStatus = Literal["unverified", "verified", "rejected"]


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    document_name: str
    document_type: str
    academic_year: str | None
    version: str
    effective_date: str | None
    source_type: str
    verification_status: VerificationStatus
    vector_sync_status: Literal["synced", "pending"]
    processing_status: str
    uploaded_at: datetime
    uploaded_by_user_id: int | None = None
    uploaded_by_username: str | None = None
    page_count: int | None = None
    chunk_count: int | None = None
    reviewed_by_user_id: int | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None


class VerificationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["verified", "rejected"]
    review_note: str | None = Field(default=None, max_length=2000)

    @field_validator("review_note")
    @classmethod
    def trim_review_note(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None
