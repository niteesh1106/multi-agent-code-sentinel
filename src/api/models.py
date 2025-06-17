"""
Pydantic models for API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class WebhookPayload(BaseModel):
    """GitHub webhook payload."""
    action: str
    pull_request: Optional[Dict[str, Any]] = None
    repository: Dict[str, Any]
    sender: Dict[str, Any]


class ReviewRequest(BaseModel):
    """Manual review request."""
    repo: str = Field(..., example="owner/repository")
    pr_number: int = Field(..., example=123, ge=1)
    post_comment: bool = Field(True, description="Post review as GitHub comment")
    include_details: bool = Field(False, description="Include detailed report in response")


class ReviewResponse(BaseModel):
    """Review response."""
    review_id: str
    status: str
    message: str
    started_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    agents: List[str]
    agents_status: Optional[Dict[str, str]] = None
    timestamp: str


class ReviewStatus(BaseModel):
    """Review status details."""
    status: str = Field(..., description="pending | in_progress | completed | failed")
    started_at: str
    completed_at: Optional[str] = None
    pr_number: int
    repo: str
    summary: Optional[Dict[str, Any]] = None
    total_issues: Optional[int] = None
    critical_issues: Optional[int] = None
    error: Optional[str] = None
    report: Optional[Dict[str, Any]] = None