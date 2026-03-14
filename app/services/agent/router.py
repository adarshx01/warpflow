"""
Agent router: workflow execution endpoints.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserSecret, Workflow
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.security import decrypt_value
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


async def _load_api_key(db: AsyncSession, owner_id: uuid.UUID, ai_provider: str) -> str:
    """Fetch and decrypt the stored API key for the given provider."""
    secret_key = "agent_openai_api_key" if ai_provider == "openai" else "agent_gemini_api_key"
    result = await db.execute(
        select(UserSecret).where(
            UserSecret.owner_id == owner_id,
            UserSecret.secret_key == secret_key,
        )
    )
    secret = result.scalar_one_or_none()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"No {ai_provider.capitalize()} API key found. "
                "Please save your API key in the AI Agent node configuration."
            ),
        )
    decrypted = decrypt_value(secret.encrypted_value)
    if not decrypted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Stored API key is empty. Please reset and re-enter it.",
        )
    return decrypted


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

    api_key = await _load_api_key(db, current_user.id, body.ai_provider)

    engine = WorkflowEngine(
        db=db,
        user=current_user,
        nodes=workflow.nodes or [],
        connections=workflow.connections or [],
        workflow_id=str(workflow.id),
    )
    return await engine.execute(
        prompt=body.prompt,
        ai_provider=body.ai_provider,
        ai_api_key=api_key,
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
    api_key = await _load_api_key(db, current_user.id, body.ai_provider)

    engine = WorkflowEngine(
        db=db,
        user=current_user,
        nodes=body.nodes,
        connections=body.connections,
        workflow_id="inline",
    )
    return await engine.execute(
        prompt=body.prompt,
        ai_provider=body.ai_provider,
        ai_api_key=api_key,
        ai_model=body.ai_model,
    )
