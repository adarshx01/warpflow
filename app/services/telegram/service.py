"""
Telegram Bot API service — wraps all major Telegram Bot API operations.
Uses the Bot Token from the node config. No OAuth required.
All calls go to https://api.telegram.org/bot<token>/<method>
"""
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

TGRAM_API = "https://api.telegram.org"


async def _call(token: str, method: str, payload: dict) -> dict:
    """POST to the Telegram Bot API and return the result dict."""
    url = f"{TGRAM_API}/bot{token}/{method}"
    # Remove None values so Telegram doesn't complain
    body = {k: v for k, v in payload.items() if v is not None}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(
                f"Telegram API error ({method}): {data.get('description', 'unknown')}"
            )
        return data.get("result", data)


# ── Bot Info ──────────────────────────────────────────────────────────────────

async def telegram_get_me(token: str, params: dict[str, Any]) -> dict:
    """Get basic information about the bot."""
    return await _call(token, "getMe", {})


async def telegram_get_my_commands(token: str, params: dict[str, Any]) -> dict:
    """Get the current list of bot commands."""
    return await _call(token, "getMyCommands", {
        "scope": params.get("scope"),
        "language_code": params.get("language_code"),
    })


async def telegram_set_my_commands(token: str, params: dict[str, Any]) -> dict:
    """Set the list of bot commands."""
    return await _call(token, "setMyCommands", {
        "commands": params["commands"],  # list of {command, description}
        "scope": params.get("scope"),
        "language_code": params.get("language_code"),
    })


# ── Messaging ─────────────────────────────────────────────────────────────────

async def telegram_send_message(token: str, params: dict[str, Any]) -> dict:
    """Send a text message to a chat. Supports HTML and Markdown formatting."""
    return await _call(token, "sendMessage", {
        "chat_id": params["chat_id"],
        "text": params["text"],
        "parse_mode": params.get("parse_mode", "HTML"),
        "reply_to_message_id": params.get("reply_to_message_id"),
        "disable_web_page_preview": params.get("disable_web_page_preview", False),
        "disable_notification": params.get("disable_notification", False),
        "protect_content": params.get("protect_content", False),
    })


async def telegram_edit_message(token: str, params: dict[str, Any]) -> dict:
    """Edit the text of an existing message."""
    return await _call(token, "editMessageText", {
        "chat_id": params["chat_id"],
        "message_id": params["message_id"],
        "text": params["text"],
        "parse_mode": params.get("parse_mode", "HTML"),
        "disable_web_page_preview": params.get("disable_web_page_preview", False),
    })


async def telegram_delete_message(token: str, params: dict[str, Any]) -> dict:
    """Delete a message from a chat."""
    return await _call(token, "deleteMessage", {
        "chat_id": params["chat_id"],
        "message_id": params["message_id"],
    })


async def telegram_forward_message(token: str, params: dict[str, Any]) -> dict:
    """Forward a message from one chat to another."""
    return await _call(token, "forwardMessage", {
        "chat_id": params["chat_id"],
        "from_chat_id": params["from_chat_id"],
        "message_id": params["message_id"],
        "disable_notification": params.get("disable_notification", False),
    })


async def telegram_copy_message(token: str, params: dict[str, Any]) -> dict:
    """Copy a message to another chat (without the forwarded-from tag)."""
    return await _call(token, "copyMessage", {
        "chat_id": params["chat_id"],
        "from_chat_id": params["from_chat_id"],
        "message_id": params["message_id"],
        "caption": params.get("caption"),
        "parse_mode": params.get("parse_mode", "HTML"),
    })


async def telegram_pin_message(token: str, params: dict[str, Any]) -> dict:
    """Pin a message in a chat."""
    return await _call(token, "pinChatMessage", {
        "chat_id": params["chat_id"],
        "message_id": params["message_id"],
        "disable_notification": params.get("disable_notification", False),
    })


async def telegram_unpin_message(token: str, params: dict[str, Any]) -> dict:
    """Unpin a specific message in a chat."""
    return await _call(token, "unpinChatMessage", {
        "chat_id": params["chat_id"],
        "message_id": params.get("message_id"),
    })


async def telegram_unpin_all_messages(token: str, params: dict[str, Any]) -> dict:
    """Unpin all pinned messages in a chat."""
    return await _call(token, "unpinAllChatMessages", {
        "chat_id": params["chat_id"],
    })


# ── Media ─────────────────────────────────────────────────────────────────────

async def telegram_send_photo(token: str, params: dict[str, Any]) -> dict:
    """Send a photo to a chat. Provide a file_id or a public URL."""
    return await _call(token, "sendPhoto", {
        "chat_id": params["chat_id"],
        "photo": params["photo"],  # file_id or URL
        "caption": params.get("caption"),
        "parse_mode": params.get("parse_mode", "HTML"),
        "reply_to_message_id": params.get("reply_to_message_id"),
    })


async def telegram_send_document(token: str, params: dict[str, Any]) -> dict:
    """Send a document/file to a chat."""
    return await _call(token, "sendDocument", {
        "chat_id": params["chat_id"],
        "document": params["document"],  # file_id or URL
        "caption": params.get("caption"),
        "parse_mode": params.get("parse_mode", "HTML"),
    })


async def telegram_send_audio(token: str, params: dict[str, Any]) -> dict:
    """Send an audio file to a chat."""
    return await _call(token, "sendAudio", {
        "chat_id": params["chat_id"],
        "audio": params["audio"],
        "caption": params.get("caption"),
        "title": params.get("title"),
        "performer": params.get("performer"),
        "duration": params.get("duration"),
    })


async def telegram_send_video(token: str, params: dict[str, Any]) -> dict:
    """Send a video to a chat."""
    return await _call(token, "sendVideo", {
        "chat_id": params["chat_id"],
        "video": params["video"],
        "caption": params.get("caption"),
        "parse_mode": params.get("parse_mode", "HTML"),
        "duration": params.get("duration"),
        "width": params.get("width"),
        "height": params.get("height"),
    })


async def telegram_send_animation(token: str, params: dict[str, Any]) -> dict:
    """Send a GIF or animation to a chat."""
    return await _call(token, "sendAnimation", {
        "chat_id": params["chat_id"],
        "animation": params["animation"],
        "caption": params.get("caption"),
        "parse_mode": params.get("parse_mode", "HTML"),
    })


async def telegram_send_sticker(token: str, params: dict[str, Any]) -> dict:
    """Send a sticker to a chat using its file_id."""
    return await _call(token, "sendSticker", {
        "chat_id": params["chat_id"],
        "sticker": params["sticker"],
    })


async def telegram_send_location(token: str, params: dict[str, Any]) -> dict:
    """Send a map location to a chat."""
    return await _call(token, "sendLocation", {
        "chat_id": params["chat_id"],
        "latitude": params["latitude"],
        "longitude": params["longitude"],
        "horizontal_accuracy": params.get("horizontal_accuracy"),
        "live_period": params.get("live_period"),
    })


async def telegram_send_poll(token: str, params: dict[str, Any]) -> dict:
    """Send a poll to a chat."""
    return await _call(token, "sendPoll", {
        "chat_id": params["chat_id"],
        "question": params["question"],
        "options": params["options"],  # list of strings
        "is_anonymous": params.get("is_anonymous", True),
        "type": params.get("type", "regular"),  # regular or quiz
        "allows_multiple_answers": params.get("allows_multiple_answers", False),
        "correct_option_id": params.get("correct_option_id"),
        "explanation": params.get("explanation"),
    })


# ── Chat Management ───────────────────────────────────────────────────────────

async def telegram_get_chat(token: str, params: dict[str, Any]) -> dict:
    """Get information about a chat (group, channel, or private)."""
    return await _call(token, "getChat", {"chat_id": params["chat_id"]})


async def telegram_get_chat_member_count(token: str, params: dict[str, Any]) -> dict:
    """Get the number of members in a chat."""
    return await _call(token, "getChatMemberCount", {"chat_id": params["chat_id"]})


async def telegram_get_chat_member(token: str, params: dict[str, Any]) -> dict:
    """Get information about a specific member in a chat."""
    return await _call(token, "getChatMember", {
        "chat_id": params["chat_id"],
        "user_id": params["user_id"],
    })


async def telegram_ban_chat_member(token: str, params: dict[str, Any]) -> dict:
    """Ban a user from a group or channel."""
    return await _call(token, "banChatMember", {
        "chat_id": params["chat_id"],
        "user_id": params["user_id"],
        "until_date": params.get("until_date"),
        "revoke_messages": params.get("revoke_messages", False),
    })


async def telegram_unban_chat_member(token: str, params: dict[str, Any]) -> dict:
    """Unban a user from a group or channel."""
    return await _call(token, "unbanChatMember", {
        "chat_id": params["chat_id"],
        "user_id": params["user_id"],
        "only_if_banned": params.get("only_if_banned", True),
    })


async def telegram_restrict_chat_member(token: str, params: dict[str, Any]) -> dict:
    """Restrict a user in a group (mute, limit media, etc.)."""
    return await _call(token, "restrictChatMember", {
        "chat_id": params["chat_id"],
        "user_id": params["user_id"],
        "permissions": params["permissions"],  # ChatPermissions object
        "until_date": params.get("until_date"),
    })


async def telegram_promote_chat_member(token: str, params: dict[str, Any]) -> dict:
    """Promote or demote a user as admin in a group or channel."""
    return await _call(token, "promoteChatMember", {
        "chat_id": params["chat_id"],
        "user_id": params["user_id"],
        "can_manage_chat": params.get("can_manage_chat"),
        "can_post_messages": params.get("can_post_messages"),
        "can_edit_messages": params.get("can_edit_messages"),
        "can_delete_messages": params.get("can_delete_messages"),
        "can_invite_users": params.get("can_invite_users"),
        "can_pin_messages": params.get("can_pin_messages"),
    })


async def telegram_set_chat_title(token: str, params: dict[str, Any]) -> dict:
    """Change the title of a group or channel."""
    return await _call(token, "setChatTitle", {
        "chat_id": params["chat_id"],
        "title": params["title"],
    })


async def telegram_set_chat_description(token: str, params: dict[str, Any]) -> dict:
    """Change the description of a group, supergroup, or channel."""
    return await _call(token, "setChatDescription", {
        "chat_id": params["chat_id"],
        "description": params.get("description", ""),
    })


async def telegram_leave_chat(token: str, params: dict[str, Any]) -> dict:
    """Make the bot leave a group, supergroup, or channel."""
    return await _call(token, "leaveChat", {"chat_id": params["chat_id"]})


async def telegram_export_invite_link(token: str, params: dict[str, Any]) -> dict:
    """Generate a new primary invite link for a chat."""
    return await _call(token, "exportChatInviteLink", {"chat_id": params["chat_id"]})


# ── Files ────────────────────────────────────────────────────────────────────

async def telegram_get_file(token: str, params: dict[str, Any]) -> dict:
    """Get info and a download link for a file by its file_id."""
    result = await _call(token, "getFile", {"file_id": params["file_id"]})
    # Attach the full download URL for convenience
    file_path = result.get("file_path", "")
    if file_path:
        result["download_url"] = f"https://api.telegram.org/file/bot{token}/{file_path}"
    return result


# ── Inline / Callbacks ────────────────────────────────────────────────────────

async def telegram_answer_callback_query(token: str, params: dict[str, Any]) -> dict:
    """Answer a callback query (from inline keyboard button presses)."""
    return await _call(token, "answerCallbackQuery", {
        "callback_query_id": params["callback_query_id"],
        "text": params.get("text"),
        "show_alert": params.get("show_alert", False),
        "url": params.get("url"),
        "cache_time": params.get("cache_time", 0),
    })


# ── Webhooks ─────────────────────────────────────────────────────────────────

async def telegram_set_webhook(token: str, params: dict[str, Any]) -> dict:
    """Set a webhook URL to receive updates."""
    return await _call(token, "setWebhook", {
        "url": params["url"],
        "max_connections": params.get("max_connections", 40),
        "allowed_updates": params.get("allowed_updates"),
        "drop_pending_updates": params.get("drop_pending_updates", False),
    })


async def telegram_delete_webhook(token: str, params: dict[str, Any]) -> dict:
    """Remove the webhook and switch back to getUpdates polling."""
    return await _call(token, "deleteWebhook", {
        "drop_pending_updates": params.get("drop_pending_updates", False),
    })


async def telegram_get_webhook_info(token: str, params: dict[str, Any]) -> dict:
    """Get current webhook status."""
    return await _call(token, "getWebhookInfo", {})
