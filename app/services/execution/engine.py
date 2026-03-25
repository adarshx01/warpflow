import logging
import uuid
from collections import deque
from typing import Any, Dict

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Workflow, User, UserSecret
from app.security import decrypt_value
from app.services.agent.engine import WorkflowEngine
from app.services.google.common import get_user_credential, get_valid_access_token
from app.services.google.google_workspace_service import (
    GoogleWorkspaceService,
    GOOGLE_NODE_TYPES,
)

logger = logging.getLogger(__name__)

DEFAULT_PROMPT_TEMPLATE = (
    "A new news article has just been published: \"{title}\"\n"
    "URL: {url}\n"
    "Snippet: {snippet}\n\n"
    "Please summarize this article in 2-3 sentences and send the summary to the configured Slack channel."
)

# Node types that are entry-points only (no operation to execute)
_TRIGGER_NODE_TYPES = {
    "manual-trigger",
    "schedule-trigger",
    "webhook-trigger",
    "email-trigger",
    "news-trigger",
    "slack-trigger",
    "telegram-trigger",
}


async def execute_direct_workflow(
    db: AsyncSession,
    wf: Workflow,
    trigger_data: Dict[str, Any],
) -> None:
    """
    Execute a workflow that has NO ai-agent node by walking the node graph
    and calling each connected service node directly.

    Currently supports all Google Workspace node types:
      google-sheets, google-docs, google-drive, gmail, google-forms

    Steps
    -----
    1. Build an adjacency map from the workflow connections.
    2. BFS from every trigger node to collect downstream service nodes in order.
    3. For each service node, resolve OAuth credential → access token.
    4. Instantiate GoogleWorkspaceService and dispatch the configured operation.
    5. Store previous step output in `context` so later nodes can reference it.
    """
    nodes: list[dict] = wf.nodes or []
    connections: list[dict] = wf.connections or []

    # Build id → node map
    node_map: dict[str, dict] = {n["id"]: n for n in nodes}

    # Build directed adjacency: source → {targets}
    adj: dict[str, set[str]] = {n["id"]: set() for n in nodes}
    for conn in connections:
        src = conn.get("from") or conn.get("sourceId", "")
        tgt = conn.get("to") or conn.get("targetId", "")
        if src in adj:
            adj[src].add(tgt)

    # Collect trigger nodes as BFS starting points
    trigger_nodes = [n for n in nodes if n.get("type", "") in _TRIGGER_NODE_TYPES]
    if not trigger_nodes:
        # Fall back to nodes with no incoming edges
        incoming: set[str] = {
            tgt
            for conn in connections
            for tgt in [(conn.get("to") or conn.get("targetId", ""))]
            if tgt
        }
        trigger_nodes = [n for n in nodes if n["id"] not in incoming]

    # BFS traversal
    visited: set[str] = set()
    queue: deque[str] = deque(n["id"] for n in trigger_nodes)
    execution_order: list[dict] = []

    while queue:
        nid = queue.popleft()
        if nid in visited:
            continue
        visited.add(nid)
        node = node_map.get(nid)
        if node and node.get("type", "") not in _TRIGGER_NODE_TYPES:
            execution_order.append(node)
        for neighbor in adj.get(nid, set()):
            if neighbor not in visited:
                queue.append(neighbor)

    if not execution_order:
        logger.warning(
            "Workflow %s: No executable service nodes found downstream of triggers.",
            wf.id,
        )
        return

    logger.info(
        "⚡ Direct execution for Workflow %s — %d node(s): %s",
        wf.id,
        len(execution_order),
        [n.get("type") for n in execution_order],
    )

    # Load the workflow owner
    user = await db.get(User, wf.owner_id)
    if not user:
        logger.error("Workflow %s: Owner user not found — skipping.", wf.id)
        return

    context: Dict[str, Any] = {"trigger": trigger_data}

    for node in execution_order:
        node_type = node.get("type", "")
        node_data = node.get("data", {})
        node_id = node.get("id", "?")

        # ── Google Workspace nodes ────────────────────────
        if node_type in GOOGLE_NODE_TYPES:
            credential_id = node_data.get("credentialId")
            operation = node_data.get("operation", "")
            params: Dict[str, Any] = node_data.get("params") or {}

            if not credential_id:
                logger.warning(
                    "Workflow %s: Node %s (%s) has no credentialId — skipping.",
                    wf.id, node_id, node_type,
                )
                continue

            if not operation:
                logger.warning(
                    "Workflow %s: Node %s (%s) has no operation configured — skipping.",
                    wf.id, node_id, node_type,
                )
                continue

            try:
                credential = await get_user_credential(
                    db, uuid.UUID(str(credential_id)), user.id
                )
                token = await get_valid_access_token(credential, db)
            except Exception as exc:
                logger.error(
                    "Workflow %s: Node %s (%s) failed credential resolution: %s",
                    wf.id, node_id, node_type, exc,
                )
                continue

            svc = GoogleWorkspaceService(token)
            try:
                result = await svc.execute(node_type, operation, params)
                context[node_id] = result
                logger.info(
                    "✅ Workflow %s: Node %s (%s → %s) succeeded. Keys: %s",
                    wf.id, node_id, node_type, operation,
                    list(result.keys()) if isinstance(result, dict) else type(result).__name__,
                )
            except Exception as exc:
                logger.error(
                    "❌ Workflow %s: Node %s (%s → %s) failed: %s",
                    wf.id, node_id, node_type, operation, exc,
                )
                context[f"{node_id}_error"] = str(exc)

        else:
            logger.info(
                "Workflow %s: Node %s (%s) is not a supported direct-execution type — skipping.",
                wf.id, node_id, node_type,
            )

    logger.info("✅ Direct execution of Workflow %s complete.", wf.id)


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
        # ── NEW: Direct execution path (no AI agent required) ──────────
        logger.info(
            "Workflow %s has no ai-agent node — attempting direct service execution.",
            workflow_id,
        )
        await execute_direct_workflow(db, wf, trigger_data)
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
