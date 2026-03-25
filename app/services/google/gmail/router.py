"""
Gmail router: OAuth2 flow + execute endpoint for Gmail API v1.
"""
import base64
import logging
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.auth.utils import get_current_user
from app.rate_limit import limiter
from app.services.google.common import (
    get_user_credential, get_valid_access_token,
    auth_headers, handle_google_error,
    google_oauth_start, google_oauth_callback,
)
from app.services.google.gmail.schemas import GmailExecuteRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gmail", tags=["gmail"])

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
REDIRECT_URI = "http://localhost:8000/api/gmail/oauth/callback"
FRONTEND_SUCCESS_URL = "http://localhost:5173?google_auth=success"


# ── OAuth ────────────────────────────────────

@router.get("/oauth/start")
async def oauth_start(
    credential_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cred = await get_user_credential(db, credential_id, current_user.id)
    url = await google_oauth_start(cred, GOOGLE_SCOPES, REDIRECT_URI)
    return RedirectResponse(url=url)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str, state: str, db: AsyncSession = Depends(get_db),
):
    await google_oauth_callback(code, state, REDIRECT_URI, db, FRONTEND_SUCCESS_URL)
    return RedirectResponse(url=FRONTEND_SUCCESS_URL)


# ── Gmail API helpers ────────────────────────

async def send_email(token: str, params: dict[str, Any]) -> dict:
    """Send an email via Gmail API."""
    to = params.get("to")
    subject = params.get("subject", "")
    body_text = params.get("body", "")
    body_html = params.get("bodyHtml")
    cc = params.get("cc")
    bcc = params.get("bcc")

    if not to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'to' is required")

    if body_html:
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(body_html, "html"))
    else:
        message = MIMEText(body_text)

    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    if bcc:
        message["bcc"] = bcc

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{GMAIL_API_BASE}/messages/send",
                headers=auth_headers(token),
                json={"raw": raw},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    result = resp.json()
    return {
        "messageId": result.get("id"),
        "threadId": result.get("threadId"),
        "labelIds": result.get("labelIds", []),
    }


async def list_messages(token: str, params: dict[str, Any]) -> dict:
    """List messages in the user's mailbox."""
    max_results = min(params.get("maxResults", 20), 100)
    page_token = params.get("pageToken")
    label_ids = params.get("labelIds", ["INBOX"])
    query = params.get("query", "")

    api_params: dict[str, Any] = {"maxResults": max_results}
    if page_token:
        api_params["pageToken"] = page_token
    if label_ids:
        api_params["labelIds"] = label_ids
    if query:
        api_params["q"] = query

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{GMAIL_API_BASE}/messages",
                headers=auth_headers(token),
                params=api_params,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    data = resp.json()
    messages = data.get("messages", [])

    # Fetch summary for each message
    summaries = []
    async with httpx.AsyncClient() as client:
        for msg in messages[:max_results]:
            try:
                msg_resp = await client.get(
                    f"{GMAIL_API_BASE}/messages/{msg['id']}",
                    headers=auth_headers(token),
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                )
                msg_resp.raise_for_status()
                msg_data = msg_resp.json()
                headers_list = msg_data.get("payload", {}).get("headers", [])
                header_dict = {h["name"]: h["value"] for h in headers_list}
                summaries.append({
                    "id": msg["id"],
                    "threadId": msg.get("threadId"),
                    "from": header_dict.get("From", ""),
                    "subject": header_dict.get("Subject", ""),
                    "date": header_dict.get("Date", ""),
                    "snippet": msg_data.get("snippet", ""),
                    "labelIds": msg_data.get("labelIds", []),
                })
            except httpx.HTTPStatusError:
                continue

    return {
        "messages": summaries,
        "nextPageToken": data.get("nextPageToken"),
        "resultSizeEstimate": data.get("resultSizeEstimate", 0),
    }


async def get_message(token: str, params: dict[str, Any]) -> dict:
    """Get a specific message by ID."""
    message_id = params.get("messageId")
    if not message_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="messageId is required")

    fmt = params.get("format", "full")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{GMAIL_API_BASE}/messages/{message_id}",
                headers=auth_headers(token),
                params={"format": fmt},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    msg_data = resp.json()

    # Extract body text
    body_text = ""
    payload = msg_data.get("payload", {})
    if payload.get("body", {}).get("data"):
        body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break

    headers_list = payload.get("headers", [])
    header_dict = {h["name"]: h["value"] for h in headers_list}

    return {
        "id": msg_data.get("id"),
        "threadId": msg_data.get("threadId"),
        "from": header_dict.get("From", ""),
        "to": header_dict.get("To", ""),
        "subject": header_dict.get("Subject", ""),
        "date": header_dict.get("Date", ""),
        "body": body_text,
        "snippet": msg_data.get("snippet", ""),
        "labelIds": msg_data.get("labelIds", []),
    }


async def search_messages(token: str, params: dict[str, Any]) -> dict:
    """Search messages using Gmail query syntax."""
    query = params.get("query", "")
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query is required")
    params["query"] = query
    return await list_messages(token, params)


async def trash_message(token: str, params: dict[str, Any]) -> dict:
    """Move a message to trash."""
    message_id = params.get("messageId")
    if not message_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="messageId is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{GMAIL_API_BASE}/messages/{message_id}/trash",
                headers=auth_headers(token),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return {"success": True, "messageId": message_id, "message": "Message moved to trash"}


async def list_labels(token: str, params: dict[str, Any]) -> dict:
    """List all labels in the mailbox."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{GMAIL_API_BASE}/labels",
                headers=auth_headers(token),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return resp.json()


# ── Execute endpoint ─────────────────────────

@router.post("/execute")
@limiter.limit("30/minute")
async def execute(
    request: Request,
    body: GmailExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    credential = await get_user_credential(db, body.credentialId, current_user.id)
    token = await get_valid_access_token(credential, db)

    match body.operation:
        case "send_email":
            return await send_email(token, body.params)
        case "list_messages":
            return await list_messages(token, body.params)
        case "get_message":
            return await get_message(token, body.params)
        case "search_messages":
            return await search_messages(token, body.params)
        case "trash_message":
            return await trash_message(token, body.params)
        case "list_labels":
            return await list_labels(token, body.params)
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {body.operation}",
            )
