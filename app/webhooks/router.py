import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Workflow
from app.rate_limit import limiter
from app.services.execution.engine import start_workflow

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

async def _get_workflow_with_webhook(db: AsyncSession, workflow_id: str) -> Workflow:
    stmt = select(Workflow).where(Workflow.id == workflow_id)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )
        
    # Check if there is a webhook node in the workflow
    nodes = workflow.nodes or []
    has_webhook = any(node.get("type") == "webhook" for node in nodes)
    
    if not has_webhook:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow does not have a Webhook Trigger node.",
        )
        
    # Also verify the workflow is active if it's an automated trigger
    if not workflow.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow is not active.",
        )
        
    return workflow

@router.post("/api/webhooks/{workflow_id}")
@router.get("/api/webhooks/{workflow_id}")
@limiter.limit("100/minute")
async def execute_webhook(
    request: Request,
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a workflow via an incoming Webhook.
    Accepts GET or POST requests and extracts query params/body to pass as payload.
    """
    workflow = await _get_workflow_with_webhook(db, workflow_id)
    
    # Locate the webhook node to check for secretToken
    webhook_node = next((node for node in (workflow.nodes or []) if node.get("type") == "webhook"), None)
    if webhook_node:
        config = webhook_node.get("data", {})
        secret_token = config.get("secretToken")
        
        # If a secret token is configured, validate the header
        if secret_token:
            provided_token = request.headers.get("x-warpcore-signature")
            if not provided_token or provided_token != secret_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or missing X-WarpCore-Signature header",
                )
    
    # Extract request data
    payload = {}
    if request.method == "POST":
        try:
            payload["body"] = await request.json()
        except Exception:
            # If not JSON, try text or form
            payload["body"] = {}
            
    payload["query_params"] = dict(request.query_params)
    payload["headers"] = dict(request.headers)
        
    await start_workflow(db, workflow.id, trigger_data={"source": "webhook", "payload": payload})
    return {"status": "success", "message": "Webhook received and workflow triggered"}
