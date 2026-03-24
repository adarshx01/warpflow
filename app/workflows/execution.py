import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, Workflow
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.services.execution.engine import start_workflow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["execution"])

async def _get_workflow_with_manual_trigger(db: AsyncSession, workflow_id: str) -> Workflow:
    stmt = select(Workflow).where(Workflow.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
        
    # Check if there is a manual-trigger node in the workflow
    nodes = workflow.nodes or []
    has_manual_trigger = any(node.get("type") == "manual-trigger" for node in nodes)
    
    if not has_manual_trigger:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow does not have a Manual Trigger node.",
        )
        
    return workflow

@router.post("/api/workflows/{workflow_id}/execute")
@limiter.limit("20/minute")
async def execute_workflow_authenticated(
    request: Request,
    workflow_id: str,
    payload: Dict[str, Any] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a workflow manually from the UI.
    Requires authentication and verifies ownership.
    """
    payload = payload or {}
    workflow = await _get_workflow_with_manual_trigger(db, workflow_id)
    
    if workflow.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to execute this workflow",
        )
        
    await start_workflow(db, workflow.id, trigger_data={"source": "frontend_manual", "payload": payload})
    return {"status": "success", "message": "Workflow execution started"}

@router.post("/api/trigger/{workflow_id}")
@limiter.limit("60/minute")
async def execute_workflow_external(
    request: Request,
    workflow_id: str,
    token: str = None,
    payload: Dict[str, Any] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a workflow manually from an external source (e.g., mobile shortcut, external script).
    Currently uses the workflow_id (UUID) as a shared secret, with an optional token field.
    """
    payload = payload or {}
    workflow = await _get_workflow_with_manual_trigger(db, workflow_id)
    
    # Locate the manual trigger node
    manual_node = next((node for node in (workflow.nodes or []) if node.get("type") == "manual-trigger"), None)
    if manual_node:
        config = manual_node.get("data", {})
        # Merge if test payload is defined, overriding with request payload if necessary
        test_payload = config.get("payload", {})
        payload = {**test_payload, **payload}
        
    await start_workflow(db, workflow.id, trigger_data={"source": "external_api", "payload": payload})
    return {"status": "success", "message": "Workflow triggered successfully"}
