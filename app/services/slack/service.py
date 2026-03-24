"""
Slack service — wraps the Slack Web API for all major operations.
Uses a Bot Token (xoxb-...) stored in the node's data configuration.
"""
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"


async def _call(token: str, method: str, payload: dict) -> dict:
    """Make an authenticated POST to the Slack Web API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{SLACK_API}/{method}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack API error ({method}): {data.get('error', 'unknown')}")
        return data


# ── Messaging ────────────────────────────────────────────────────────────────

async def slack_send_message(token: str, params: dict[str, Any]) -> dict:
    """Send a message to a channel or user."""
    return await _call(token, "chat.postMessage", {
        "channel": params["channel"],
        "text": params.get("text", ""),
        "blocks": params.get("blocks"),
        "username": params.get("username"),
        "icon_emoji": params.get("icon_emoji"),
        "thread_ts": params.get("thread_ts"),
        "attachments": params.get("attachments"),
    })


async def slack_update_message(token: str, params: dict[str, Any]) -> dict:
    """Update an existing message."""
    return await _call(token, "chat.update", {
        "channel": params["channel"],
        "ts": params["ts"],
        "text": params.get("text", ""),
        "blocks": params.get("blocks"),
    })


async def slack_delete_message(token: str, params: dict[str, Any]) -> dict:
    """Delete a message."""
    return await _call(token, "chat.delete", {
        "channel": params["channel"],
        "ts": params["ts"],
    })


async def slack_get_permalink(token: str, params: dict[str, Any]) -> dict:
    """Get a permanent link to a specific message."""
    return await _call(token, "chat.getPermalink", {
        "channel": params["channel"],
        "message_ts": params["message_ts"],
    })


# ── Channels ─────────────────────────────────────────────────────────────────

async def slack_list_channels(token: str, params: dict[str, Any]) -> dict:
    """List public and private channels the bot has access to."""
    return await _call(token, "conversations.list", {
        "limit": params.get("limit", 100),
        "types": params.get("types", "public_channel,private_channel"),
        "exclude_archived": params.get("exclude_archived", True),
    })


async def slack_get_channel_info(token: str, params: dict[str, Any]) -> dict:
    """Get detailed information about a channel."""
    return await _call(token, "conversations.info", {"channel": params["channel"]})


async def slack_get_channel_history(token: str, params: dict[str, Any]) -> dict:
    """Fetch messages from a channel."""
    payload = {
        "channel": params["channel"],
        "limit": params.get("limit", 20),
    }
    if params.get("oldest"):
        payload["oldest"] = params["oldest"]
    if params.get("latest"):
        payload["latest"] = params["latest"]
    return await _call(token, "conversations.history", payload)


async def slack_get_thread_replies(token: str, params: dict[str, Any]) -> dict:
    """Get all replies in a message thread."""
    return await _call(token, "conversations.replies", {
        "channel": params["channel"],
        "ts": params["ts"],
        "limit": params.get("limit", 50),
    })


async def slack_invite_to_channel(token: str, params: dict[str, Any]) -> dict:
    """Invite one or more users to a channel."""
    return await _call(token, "conversations.invite", {
        "channel": params["channel"],
        "users": params["users"],  # comma-separated user IDs
    })


async def slack_create_channel(token: str, params: dict[str, Any]) -> dict:
    """Create a new channel."""
    return await _call(token, "conversations.create", {
        "name": params["name"],
        "is_private": params.get("is_private", False),
    })


async def slack_archive_channel(token: str, params: dict[str, Any]) -> dict:
    """Archive a channel."""
    return await _call(token, "conversations.archive", {"channel": params["channel"]})


# ── Users ─────────────────────────────────────────────────────────────────────

async def slack_list_users(token: str, params: dict[str, Any]) -> dict:
    """List all users in the workspace."""
    return await _call(token, "users.list", {"limit": params.get("limit", 200)})


async def slack_get_user_info(token: str, params: dict[str, Any]) -> dict:
    """Get detailed information about a user."""
    return await _call(token, "users.info", {"user": params["user"]})


async def slack_lookup_user_by_email(token: str, params: dict[str, Any]) -> dict:
    """Look up a user by email address."""
    return await _call(token, "users.lookupByEmail", {"email": params["email"]})


async def slack_set_user_status(token: str, params: dict[str, Any]) -> dict:
    """Set the authenticated bot user's status."""
    return await _call(token, "users.profile.set", {
        "profile": {
            "status_text": params.get("status_text", ""),
            "status_emoji": params.get("status_emoji", ""),
            "status_expiration": params.get("status_expiration", 0),
        }
    })


# ── Reactions ─────────────────────────────────────────────────────────────────

async def slack_add_reaction(token: str, params: dict[str, Any]) -> dict:
    """Add an emoji reaction to a message."""
    return await _call(token, "reactions.add", {
        "channel": params["channel"],
        "timestamp": params["timestamp"],
        "name": params["name"],  # emoji name without colons, e.g. "thumbsup"
    })


async def slack_remove_reaction(token: str, params: dict[str, Any]) -> dict:
    """Remove an emoji reaction from a message."""
    return await _call(token, "reactions.remove", {
        "channel": params["channel"],
        "timestamp": params["timestamp"],
        "name": params["name"],
    })


async def slack_get_reactions(token: str, params: dict[str, Any]) -> dict:
    """Get all reactions on a message."""
    return await _call(token, "reactions.get", {
        "channel": params["channel"],
        "timestamp": params["timestamp"],
    })


# ── Files ────────────────────────────────────────────────────────────────────

async def slack_upload_file(token: str, params: dict[str, Any]) -> dict:
    """Upload a text-based file snippet to Slack channels."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{SLACK_API}/files.uploadV2",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "channels": params.get("channels", ""),
                "filename": params.get("filename", "file.txt"),
                "title": params.get("title", ""),
                "initial_comment": params.get("initial_comment", ""),
            },
            files={"file": (params.get("filename", "file.txt"), params["content"].encode(), "text/plain")},
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack files.uploadV2 error: {data.get('error', 'unknown')}")
        return data


async def slack_list_files(token: str, params: dict[str, Any]) -> dict:
    """List files shared in the workspace."""
    return await _call(token, "files.list", {
        "channel": params.get("channel"),
        "count": params.get("count", 20),
        "types": params.get("types", "all"),
    })


async def slack_delete_file(token: str, params: dict[str, Any]) -> dict:
    """Delete a file."""
    return await _call(token, "files.delete", {"file": params["file"]})


# ── Pins ──────────────────────────────────────────────────────────────────────

async def slack_pin_message(token: str, params: dict[str, Any]) -> dict:
    """Pin a message to a channel."""
    return await _call(token, "pins.add", {
        "channel": params["channel"],
        "timestamp": params["timestamp"],
    })


async def slack_unpin_message(token: str, params: dict[str, Any]) -> dict:
    """Unpin a message from a channel."""
    return await _call(token, "pins.remove", {
        "channel": params["channel"],
        "timestamp": params["timestamp"],
    })


async def slack_list_pins(token: str, params: dict[str, Any]) -> dict:
    """List all pinned items in a channel."""
    return await _call(token, "pins.list", {"channel": params["channel"]})


# ── Search ────────────────────────────────────────────────────────────────────

async def slack_search_messages(token: str, params: dict[str, Any]) -> dict:
    """Search for messages matching a query."""
    return await _call(token, "search.messages", {
        "query": params["query"],
        "count": params.get("count", 20),
        "sort": params.get("sort", "score"),
        "sort_dir": params.get("sort_dir", "desc"),
    })


# ── Workspace ─────────────────────────────────────────────────────────────────

async def slack_get_workspace_info(token: str, params: dict[str, Any]) -> dict:
    """Get information about the Slack workspace (team)."""
    return await _call(token, "team.info", {})


async def slack_get_bot_info(token: str, params: dict[str, Any]) -> dict:
    """Get info about the authenticated bot."""
    return await _call(token, "auth.test", {})


# ── Reminders ────────────────────────────────────────────────────────────────

async def slack_add_reminder(token: str, params: dict[str, Any]) -> dict:
    """Create a reminder for a user."""
    return await _call(token, "reminders.add", {
        "text": params["text"],
        "time": params["time"],  # Unix timestamp or natural language like "in 30 minutes"
        "user": params.get("user"),
    })
