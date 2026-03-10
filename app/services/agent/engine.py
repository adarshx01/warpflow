"""
AI Agent workflow execution engine.

Uses function-calling LLMs (Gemini or OpenAI) to orchestrate connected
service tools based on the user's prompt and workflow configuration.
"""

import json
import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services.google.common import get_user_credential, get_valid_access_token
from app.services.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
OPENAI_API_BASE = "https://api.openai.com/v1"
MAX_AGENT_ITERATIONS = 15

SYSTEM_PROMPT = (
    "You are an AI workflow automation agent. Execute the user's request by calling "
    "the available tools in the right order. Think step by step about what actions "
    "are needed, then call the tools to perform them. After completing all actions, "
    "provide a clear summary of everything that was done, including any IDs or URLs "
    "of created resources."
)


class WorkflowEngine:
    """Executes a workflow using an AI agent to orchestrate connected services."""

    def __init__(
        self,
        db: AsyncSession,
        user: User,
        nodes: list[dict[str, Any]],
        connections: list[dict[str, Any]],
    ):
        self.db = db
        self.user = user
        self._nodes = nodes
        self._connections = connections
        self._tool_map: dict[str, tuple[Any, str]] = {}
        self._steps: list[dict] = []

    async def execute(
        self,
        prompt: str,
        ai_provider: str,
        ai_api_key: str,
        ai_model: str | None = None,
    ) -> dict:
        """Execute the workflow with the given prompt using AI orchestration."""
        nodes = self._nodes
        connections = self._connections

        # Build bidirectional adjacency (handle both from/to and sourceId/targetId)
        neighbors: dict[str, set[str]] = {n["id"]: set() for n in nodes}
        for conn in connections:
            src = conn.get("from") or conn.get("sourceId", "")
            tgt = conn.get("to") or conn.get("targetId", "")
            if src in neighbors:
                neighbors[src].add(tgt)
            if tgt in neighbors:
                neighbors[tgt].add(src)

        # Find the AI agent node
        agent_node = next((n for n in nodes if n.get("type") == "ai-agent"), None)
        if not agent_node:
            raise HTTPException(status_code=400, detail="No AI Agent node found in workflow")

        # Collect service nodes connected to the agent
        connected_ids = neighbors.get(agent_node["id"], set())
        service_nodes = [
            n for n in nodes
            if n["id"] in connected_ids and n.get("type") != "ai-agent"
        ]

        if not service_nodes:
            raise HTTPException(
                status_code=400,
                detail="No service nodes connected to the AI Agent",
            )

        # Register tools from connected service nodes
        await self._register_tools(service_nodes)

        if not self._tool_map:
            raise HTTPException(
                status_code=400,
                detail="No valid tools could be loaded from the connected service nodes. "
                       "Ensure the service nodes have valid credentials configured.",
            )

        # Run the agent loop
        if ai_provider == "openai":
            summary = await self._run_openai_agent(
                prompt, ai_api_key, ai_model or "gpt-4o",
            )
        else:
            summary = await self._run_gemini_agent(
                prompt, ai_api_key, ai_model or "gemini-2.5-flash",
            )

        return {
            "workflow_id": str(self.workflow.id),
            "status": "completed",
            "summary": summary,
            "steps": self._steps,
        }

    # ─── Tool Registration ────────────────────

    async def _register_tools(self, service_nodes: list[dict]) -> None:
        """Register tools from connected service nodes, resolving credentials."""
        registered_types: set[str] = set()

        for node in service_nodes:
            node_type = node.get("type", "")
            if node_type in registered_types or node_type not in TOOL_REGISTRY:
                continue

            node_data = node.get("data", {})
            credential_id = node_data.get("credentialId")

            if not credential_id:
                logger.warning(
                    "Node %s (%s) has no credentialId configured, skipping",
                    node.get("id"), node_type,
                )
                continue

            try:
                credential = await get_user_credential(
                    self.db, UUID(str(credential_id)), self.user.id,
                )
                token = await get_valid_access_token(credential, self.db)
            except Exception as exc:
                logger.warning("Failed to get token for %s: %s", node_type, exc)
                continue

            for tool_def in TOOL_REGISTRY[node_type]:
                self._tool_map[tool_def["name"]] = (tool_def["_fn"], token)

            registered_types.add(node_type)

    def _get_tool_definitions(self) -> list[dict]:
        """Return tool definitions for only the registered (available) tools."""
        defs = []
        seen: set[str] = set()
        for service_tools in TOOL_REGISTRY.values():
            for tool in service_tools:
                name = tool["name"]
                if name in self._tool_map and name not in seen:
                    defs.append({
                        "name": name,
                        "description": tool["description"],
                        "parameters": tool["parameters"],
                    })
                    seen.add(name)
        return defs

    async def _execute_tool(self, tool_name: str, args: dict) -> dict:
        """Execute a registered tool and record the step."""
        if tool_name not in self._tool_map:
            error_msg = f"Unknown tool: {tool_name}"
            self._steps.append({"tool": tool_name, "params": args, "error": error_msg})
            return {"error": error_msg}

        fn, token = self._tool_map[tool_name]
        try:
            result = await fn(token, args)
            self._steps.append({"tool": tool_name, "params": args, "result": result})
            return result
        except HTTPException as exc:
            error_msg = str(exc.detail)
            self._steps.append({"tool": tool_name, "params": args, "error": error_msg})
            return {"error": error_msg}
        except Exception as exc:
            error_msg = str(exc)
            self._steps.append({"tool": tool_name, "params": args, "error": error_msg})
            return {"error": error_msg}

    # ─── Gemini Agent Loop ────────────────────

    async def _run_gemini_agent(self, prompt: str, api_key: str, model: str) -> str:
        """Run the agent loop using Gemini function calling."""
        tool_defs = self._get_tool_definitions()

        gemini_tools = [{
            "functionDeclarations": [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": _to_gemini_schema(t["parameters"]),
                }
                for t in tool_defs
            ]
        }]

        contents: list[dict[str, Any]] = [
            {"role": "user", "parts": [{"text": prompt}]},
        ]

        for _ in range(MAX_AGENT_ITERATIONS):
            body: dict[str, Any] = {
                "contents": contents,
                "tools": gemini_tools,
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 4096,
                },
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    resp = await client.post(
                        f"{GEMINI_API_BASE}/{model}:generateContent",
                        params={"key": api_key},
                        headers={"Content-Type": "application/json"},
                        json=body,
                    )
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    try:
                        detail = exc.response.json()
                    except Exception:
                        detail = exc.response.text
                    raise HTTPException(
                        status_code=502,
                        detail=f"Gemini API error: {detail}",
                    )

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return "No response from Gemini model."

            parts = candidates[0].get("content", {}).get("parts", [])

            # Check for function calls
            function_calls = [p for p in parts if "functionCall" in p]

            if not function_calls:
                # Final text response
                text = "".join(p.get("text", "") for p in parts if "text" in p)
                return text or "Task completed."

            # Append model response to conversation
            contents.append({"role": "model", "parts": parts})

            # Execute each function call and build responses
            response_parts: list[dict] = []
            for fc_part in function_calls:
                fc = fc_part["functionCall"]
                result = await self._execute_tool(fc["name"], fc.get("args", {}))
                response_parts.append({
                    "functionResponse": {
                        "name": fc["name"],
                        "response": {"content": result},
                    }
                })

            contents.append({"role": "user", "parts": response_parts})

        return "Agent reached maximum iterations. Check steps for partial results."

    # ─── OpenAI Agent Loop ────────────────────

    async def _run_openai_agent(self, prompt: str, api_key: str, model: str) -> str:
        """Run the agent loop using OpenAI function calling."""
        tool_defs = self._get_tool_definitions()

        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in tool_defs
        ]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        for _ in range(MAX_AGENT_ITERATIONS):
            body = {
                "model": model,
                "messages": messages,
                "tools": openai_tools,
                "temperature": 0.2,
                "max_tokens": 4096,
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    resp = await client.post(
                        f"{OPENAI_API_BASE}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json=body,
                    )
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    try:
                        detail = exc.response.json()
                    except Exception:
                        detail = exc.response.text
                    raise HTTPException(
                        status_code=502,
                        detail=f"OpenAI API error: {detail}",
                    )

            data = resp.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason")

            tool_calls = message.get("tool_calls", [])

            if not tool_calls or finish_reason == "stop":
                return message.get("content") or "Task completed."

            # Append the assistant message (with tool_calls) to conversation
            messages.append(message)

            # Execute tool calls and append results
            for tc in tool_calls:
                fn_info = tc.get("function", {})
                tool_name = fn_info.get("name", "")
                try:
                    tool_args = json.loads(fn_info.get("arguments", "{}"))
                except json.JSONDecodeError:
                    tool_args = {}

                result = await self._execute_tool(tool_name, tool_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, default=str),
                })

        return "Agent reached maximum iterations. Check steps for partial results."


# ─── Helpers ──────────────────────────────────

_TYPE_MAP = {
    "object": "OBJECT",
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
}


def _to_gemini_schema(schema: dict) -> dict:
    """Convert standard JSON Schema to Gemini's parameter format (uppercase types)."""
    result = dict(schema)
    if "type" in result:
        result["type"] = _TYPE_MAP.get(result["type"], result["type"])
    if "properties" in result:
        result["properties"] = {
            k: _to_gemini_schema(v) for k, v in result["properties"].items()
        }
    if "items" in result:
        result["items"] = _to_gemini_schema(result["items"])
    return result
