"""
Agent router: workflow execution endpoints.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, Workflow
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.services.agent.schemas import ExecuteWorkflowRequest, InlineExecuteRequest
from app.services.agent.engine import WorkflowEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


async def _get_user_workflow(
    db: AsyncSession, workflow_id: uuid.UUID, owner_id: uuid.UUID,
) -> Workflow:
    result = await db.execute(
        select(Workflow).where(
            Workflow.id == workflow_id, Workflow.owner_id == owner_id,
        )
    )
    wf = result.scalar_one_or_none()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.post("/workflows/{workflow_id}/execute")
@limiter.limit("10/minute")
async def execute_workflow(
    request: Request,
    workflow_id: uuid.UUID,
    body: ExecuteWorkflowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a saved workflow using the AI agent."""
    workflow = await _get_user_workflow(db, workflow_id, current_user.id)

    engine = WorkflowEngine(
        db=db,
        user=current_user,
        nodes=workflow.nodes or [],
        connections=workflow.connections or [],
    )
    return await engine.execute(
        prompt=body.prompt,
        ai_provider=body.ai_provider,
        ai_api_key=body.ai_api_key,
        ai_model=body.ai_model,
    )


@router.post("/execute")
@limiter.limit("10/minute")
async def execute_inline(
    request: Request,
    body: InlineExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a workflow from inline nodes & connections (no save required)."""
    engine = WorkflowEngine(
        db=db,
        user=current_user,
        nodes=body.nodes,
        connections=body.connections,
    )
    return await engine.execute(
        prompt=body.prompt,
        ai_provider=body.ai_provider,
        ai_api_key=body.ai_api_key,
        ai_model=body.ai_model,
    )
