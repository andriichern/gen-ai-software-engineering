"""Pydantic models for the support ticket system."""
from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from ..services.category_registry import OTHER_CATEGORY, category_registry

_CATEGORY_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_category(value: str) -> str:
    if value == OTHER_CATEGORY or category_registry.exists(value):
        return value
    raise ValueError(
        f"Unknown category '{value}'. See GET /category/list for valid categories."
    )


def _validate_category_key(value: str) -> str:
    if not _CATEGORY_KEY_PATTERN.match(value):
        raise ValueError(
            "Category key must be lowercase snake_case, starting with a letter (e.g. 'shipping_delay')"
        )
    if value == OTHER_CATEGORY:
        raise ValueError("'other' is the reserved fallback category and cannot be managed via this API")
    return value


Category = Annotated[str, AfterValidator(_validate_category)]
CategoryKey = Annotated[str, AfterValidator(_validate_category_key)]


class Priority(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(str, Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Source(str, Enum):
    WEB_FORM = "web_form"
    EMAIL = "email"
    API = "api"
    CHAT = "chat"
    PHONE = "phone"


class DeviceType(str, Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


class TicketMetadata(BaseModel):
    source: Source = Source.API
    browser: Optional[str] = None
    device_type: Optional[DeviceType] = None


class TicketCreate(BaseModel):
    customer_id: str
    customer_email: EmailStr
    customer_name: str
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    category: Optional[Category] = None
    priority: Optional[Priority] = None
    status: Status = Status.NEW
    assigned_to: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: TicketMetadata = Field(default_factory=TicketMetadata)


class TicketUpdate(BaseModel):
    """All fields optional; only provided fields are applied."""

    customer_id: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    customer_name: Optional[str] = None
    subject: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    category: Optional[Category] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    assigned_to: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[TicketMetadata] = None


class Ticket(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    customer_id: str
    customer_email: EmailStr
    customer_name: str
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    category: Category = OTHER_CATEGORY
    priority: Priority = Priority.MEDIUM
    status: Status = Status.NEW
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: TicketMetadata = Field(default_factory=TicketMetadata)
    classification_confidence: Optional[float] = None
    classification_overridden: bool = False

    @classmethod
    def from_create(cls, payload: TicketCreate) -> "Ticket":
        """Build a Ticket from a TicketCreate, letting Ticket's own defaults
        (category=OTHER, priority=MEDIUM) apply when the caller left them unset."""
        dump = payload.model_dump()
        if dump["category"] is None:
            dump.pop("category")
        if dump["priority"] is None:
            dump.pop("priority")
        return cls(**dump)


class ImportError_(BaseModel):
    index: int
    error: str


class ImportSummary(BaseModel):
    total: int
    successful: int
    failed: int
    errors: list[ImportError_] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    category: Category
    priority: Priority
    confidence: float
    reasoning: str
    keywords_found: list[str]


class CategoryKeywords(BaseModel):
    category: str
    keywords: list[str]


class CategoryCreate(BaseModel):
    key: CategoryKey
    keywords: list[str] = Field(default_factory=list)


class CategoryKeywordsUpdate(BaseModel):
    keywords: list[str]
