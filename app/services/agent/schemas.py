from pydantic import BaseModel
from typing import Any, Optional


class ExecuteWorkflowRequest(BaseModel):
    prompt: str
    ai_provider: str = "gemini"
    # ai_api_key is no longer accepted from the frontend.
    # The backend fetches the stored encrypted key automatically.
    ai_model: Optional[str] = None


class InlineExecuteRequest(BaseModel):
    """Execute a workflow without saving it first — nodes & connections sent inline."""
    nodes: list[dict[str, Any]]
    connections: list[dict[str, Any]]
    prompt: str
    ai_provider: str = "gemini"
    # ai_api_key is no longer accepted from the frontend.
    # The backend fetches the stored encrypted key automatically.
    ai_model: Optional[str] = None


class StepResult(BaseModel):
    tool: str
    params: dict[str, Any]
    result: Any = None
    error: Optional[str] = None


class ExecuteWorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    summary: str
    steps: list[StepResult]
