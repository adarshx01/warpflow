from pydantic import BaseModel, field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional, Any


# ──────────────────────────────────────────────
# Node Template Schemas
# ──────────────────────────────────────────────

class NodeTemplateResponse(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    category: str
    description: Optional[str] = None
    default_data: Optional[dict[str, Any]] = None

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# Workflow Schemas
# ──────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = "Untitled Workflow"
    description: Optional[str] = None
    nodes: Optional[list[dict[str, Any]]] = []
    connections: Optional[list[dict[str, Any]]] = []
    viewport: Optional[dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Workflow name cannot be empty")
        if len(v) > 255:
            raise ValueError("Workflow name must be at most 255 characters")
        return v


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    nodes: Optional[list[dict[str, Any]]] = None
    connections: Optional[list[dict[str, Any]]] = None
    viewport: Optional[dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Workflow name cannot be empty")
        if len(v) > 255:
            raise ValueError("Workflow name must be at most 255 characters")
        return v


class WorkflowResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    nodes: Optional[list[dict[str, Any]]] = []
    connections: Optional[list[dict[str, Any]]] = []
    viewport: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowListItem(BaseModel):
    """Lightweight response for listing workflows (no full node/connection data)."""
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    node_count: int = 0
    connection_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
