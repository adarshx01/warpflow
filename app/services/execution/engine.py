import logging
import uuid
from typing import Any, Dict

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workflow, User, UserSecret
from app.security import decrypt_value
from app.services.agent.engine import WorkflowEngine

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_TEMPLATE = (
    "A new news article has just been published: \"{title}\"\n"
    "URL: {url}\n"
    "Snippet: {snippet}\n\n"
    "Please summarize this article in 2-3 sentences and send the summary to the configured Slack channel."
)


async def start_workflow(
    db: AsyncSession,
    workflow_id: str | uuid.UUID,
    trigger_data: Dict[str, Any],
) -> None:
    """
    Real workflow execution engine.
    Fetches the workflow, resolves the AI agent node config, substitutes
    trigger_data into the prompt template, and runs WorkflowEngine.
    """
    # 1. Load the workflow
    wf = await db.get(Workflow, uuid.UUID(str(workflow_id)))
    if not wf:
        logger.error("Workflow %s not found — skipping execution.", workflow_id)
        return

    nodes = wf.nodes or []
    connections = wf.connections or []

    # 2. Find the AI agent node
    agent_node = next((n for n in nodes if n.get("type") == "ai-agent"), None)
    if not agent_node:
        logger.warning("Workflow %s has no ai-agent node — nothing to execute.", workflow_id)
        return

    agent_data = agent_node.get("data", {})
    ai_provider = agent_data.get("aiProvider", "gemini")
    ai_model = agent_data.get("aiModel") or None

    # 3. Resolve API key from per-user secrets
    secret_key = f"agent_{ai_provider}_api_key"
    stmt = sa_select(UserSecret).where(
        UserSecret.owner_id == wf.owner_id,
        UserSecret.secret_key == secret_key,
    )
    result = await db.execute(stmt)
    secret = result.scalar_one_or_none()
    if not secret:
        logger.error(
            "Workflow %s: No API key for provider '%s' (secret key: '%s'). Skipping.",
            workflow_id, ai_provider, secret_key,
        )
        return

    try:
        api_key = decrypt_value(secret.encrypted_value)
    except Exception as exc:
        logger.error("Workflow %s: Failed to decrypt API key: %s", workflow_id, exc)
        return

    # 4. Build the prompt from the template, substituting trigger payload fields
    prompt_template = agent_data.get("promptTemplate") or DEFAULT_PROMPT_TEMPLATE
    payload = trigger_data.get("payload", {})
    try:
        prompt = prompt_template.format(
            title=payload.get("title", ""),
            url=payload.get("url", ""),
            snippet=payload.get("snippet", ""),
            source=payload.get("source", ""),
            published=payload.get("published", ""),
            subject=payload.get("subject", ""),
            body=payload.get("body", ""),
        )
    except KeyError as exc:
        logger.warning("Workflow %s: Unknown placeholder in promptTemplate: %s. Using raw template.", workflow_id, exc)
        prompt = prompt_template

    # 5. Load the workflow owner user record
    user = await db.get(User, wf.owner_id)
    if not user:
        logger.error("Workflow %s: Owner user not found — skipping.", workflow_id)
        return

    # 6. Inject Slack bot token from Slack node data into node data
    #    so WorkflowEngine._register_tools can use it as a plain token.
    for node in nodes:
        if node.get("type") == "slack":
            node_data = node.get("data", {})
            token = node_data.get("botToken", "")
            # Store on the node so engine._register_tools sees it
            node["_slack_token"] = token

    # 7. Run the AI agent orchestration engine
    logger.info(
        "🚀 Executing Workflow %s | trigger: %s | provider: %s | model: %s",
        workflow_id, trigger_data.get("source", "unknown"), ai_provider, ai_model,
    )
    try:
        engine = WorkflowEngine(
            db=db,
            user=user,
            nodes=nodes,
            connections=connections,
            workflow_id=str(workflow_id),
        )
        result = await engine.execute(
            prompt=prompt,
            ai_provider=ai_provider,
            ai_api_key=api_key,
            ai_model=ai_model,
        )
        logger.info(
            "✅ Workflow %s completed. Summary: %s",
            workflow_id, str(result.get("summary", ""))[:300],
        )
    except Exception as exc:
        logger.error("❌ Workflow %s execution failed: %s", workflow_id, exc, exc_info=True)
