import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, Workflow, NodeTemplate
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.workflows.schemas import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowListItem,
    NodeTemplateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])
templates_router = APIRouter(prefix="/api/node-templates", tags=["node-templates"])


# ──────────────────────────────────────────────
# Node Templates
# ──────────────────────────────────────────────


@templates_router.get("", response_model=list[NodeTemplateResponse])
async def list_node_templates(
    category: Optional[str] = Query(None, description="Filter by category name"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List all available node templates, optionally filtered by category."""
    stmt = select(NodeTemplate).where(NodeTemplate.is_active == True)
    if category:
        stmt = stmt.where(NodeTemplate.category == category)
    stmt = stmt.order_by(NodeTemplate.category, NodeTemplate.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@templates_router.get("/categories", response_model=list[str])
async def list_template_categories(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """List all distinct node template categories."""
    stmt = (
        select(NodeTemplate.category)
        .where(NodeTemplate.is_active == True)
        .distinct()
        .order_by(NodeTemplate.category)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# ──────────────────────────────────────────────
# Workflow CRUD
# ──────────────────────────────────────────────


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_workflow(
    request: Request,
    body: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new workflow for the authenticated user."""
    workflow = Workflow(
        owner_id=current_user.id,
        name=body.name,
        description=body.description,
        nodes=body.nodes or [],
        connections=body.connections or [],
        viewport=body.viewport or {"zoom": 1, "pan": {"x": 0, "y": 0}},
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.get("", response_model=list[WorkflowListItem])
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all workflows owned by the authenticated user."""
    stmt = (
        select(Workflow)
        .where(Workflow.owner_id == current_user.id)
        .order_by(Workflow.updated_at.desc())
    )
    result = await db.execute(stmt)
    workflows = result.scalars().all()

    items = []
    for wf in workflows:
        items.append(
            WorkflowListItem(
                id=wf.id,
                name=wf.name,
                description=wf.description,
                is_active=wf.is_active,
                node_count=len(wf.nodes) if wf.nodes else 0,
                connection_count=len(wf.connections) if wf.connections else 0,
                created_at=wf.created_at,
                updated_at=wf.updated_at,
            )
        )
    return items


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single workflow by ID. Must belong to the authenticated user."""
    workflow = await _get_user_workflow(db, workflow_id, current_user.id)
    return workflow


@router.put("/{workflow_id}", response_model=WorkflowResponse)
@limiter.limit("30/minute")
async def update_workflow(
    request: Request,
    workflow_id: str,
    body: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing workflow (full or partial)."""
    workflow = await _get_user_workflow(db, workflow_id, current_user.id)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workflow, field, value)

    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a workflow. Must belong to the authenticated user."""
    workflow = await _get_user_workflow(db, workflow_id, current_user.id)
    await db.delete(workflow)
    await db.commit()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


async def _get_user_workflow(db: AsyncSession, workflow_id: str, owner_id) -> Workflow:
    """Fetch a workflow and verify ownership."""
    stmt = select(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == owner_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
    return workflow
