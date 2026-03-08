"""
Google Docs router: OAuth2 flow + execute endpoint with 5 Google API helpers.
"""
import logging
import uuid
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
from app.services.google.google_docs.schemas import ExecuteRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-docs", tags=["google-docs"])

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]
DOCS_API_BASE = "https://docs.googleapis.com/v1/documents"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3/files"
REDIRECT_URI = "http://localhost:8000/api/google-docs/oauth/callback"
FRONTEND_SUCCESS_URL = "http://localhost:5173?google_auth=success"


# ──────────────────────────────────────────────
# OAuth Flow
# ──────────────────────────────────────────────


@router.get("/oauth/start")
async def oauth_start(
    credential_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Redirect the browser to Google's OAuth consent screen."""
    cred = await get_user_credential(db, credential_id, current_user.id)
    url = await google_oauth_start(cred, GOOGLE_SCOPES, REDIRECT_URI)
    return RedirectResponse(url=url)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Exchange the auth code for tokens and store them on the credential."""
    await google_oauth_callback(code, state, REDIRECT_URI, db, FRONTEND_SUCCESS_URL)
    return RedirectResponse(url=FRONTEND_SUCCESS_URL)


# ──────────────────────────────────────────────
# Google API helpers
# ──────────────────────────────────────────────


async def create_document(token: str, params: dict[str, Any]) -> dict:
    """Create a Google Doc, optionally with content and/or moved to a folder."""
    title = params.get("title", "Untitled Document")
    content = params.get("content")
    folder_id = params.get("folderId")

    headers = auth_headers(token)

    async with httpx.AsyncClient() as client:
        # 1. Create doc
        try:
            resp = await client.post(
                DOCS_API_BASE,
                headers=headers,
                json={"title": title},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

        doc = resp.json()
        doc_id = doc["documentId"]

        # 2. Insert content if provided
        if content:
            try:
                batch_resp = await client.post(
                    f"{DOCS_API_BASE}/{doc_id}:batchUpdate",
                    headers=headers,
                    json={
                        "requests": [
                            {"insertText": {"location": {"index": 1}, "text": content}}
                        ]
                    },
                )
                batch_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                await handle_google_error(exc)

        # 3. Move to folder if provided
        if folder_id:
            try:
                move_resp = await client.patch(
                    f"{DRIVE_API_BASE}/{doc_id}",
                    headers=headers,
                    params={"addParents": folder_id, "removeParents": "root"},
                )
                move_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                await handle_google_error(exc)

    return {
        "documentId": doc_id,
        "title": title,
        "url": f"https://docs.google.com/document/d/{doc_id}/edit",
    }


async def get_document(token: str, params: dict[str, Any]) -> dict:
    """Fetch a Google Doc, optionally filtering to specific fields."""
    doc_id = params.get("documentId")
    if not doc_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documentId is required")

    fields_filter: list[str] = params.get("fields", [])

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{DOCS_API_BASE}/{doc_id}", headers=auth_headers(token))
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    doc = resp.json()

    if not fields_filter or "all" in fields_filter:
        return doc

    # Filter to requested top-level fields
    FIELD_MAP = {
        "title": "title",
        "body": "body",
        "revisionId": "revisionId",
    }
    filtered = {}
    for f in fields_filter:
        key = FIELD_MAP.get(f)
        if key and key in doc:
            filtered[key] = doc[key]
    return filtered


async def update_document(token: str, params: dict[str, Any]) -> dict:
    """Update a Google Doc using replace_body, append, or by_index mode."""
    doc_id = params.get("documentId")
    if not doc_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documentId is required")

    update_mode = params.get("updateMode", "append")
    content = params.get("content", "")
    headers = auth_headers(token)

    async with httpx.AsyncClient() as client:
        # We need the current doc for index calculations
        try:
            resp = await client.get(f"{DOCS_API_BASE}/{doc_id}", headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

        doc = resp.json()
        body_content = doc.get("body", {}).get("content", [])

        # Calculate end index of the body (last structural element's endIndex)
        end_index = 1
        for element in body_content:
            ei = element.get("endIndex")
            if ei is not None:
                end_index = ei

        if update_mode == "replace_body":
            requests = []
            # Delete all content if there is any (endIndex - 1 > 1 means there's content)
            if end_index > 2:
                requests.append({
                    "deleteContentRange": {
                        "range": {"startIndex": 1, "endIndex": end_index - 1}
                    }
                })
            requests.append({"insertText": {"location": {"index": 1}, "text": content}})

        elif update_mode == "append":
            requests = [
                {"insertText": {"location": {"index": end_index - 1}, "text": content}}
            ]

        elif update_mode == "by_index":
            para_index = params.get("paragraphIndex", 0)
            # Find the structural element at paragraphIndex in body.content
            # body.content[0] is usually a sectionBreak, paragraphs start at index 1+
            paragraphs = [e for e in body_content if "paragraph" in e]
            if para_index >= len(paragraphs):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"paragraphIndex {para_index} out of range ({len(paragraphs)} paragraphs)",
                )
            target = paragraphs[para_index]
            start_idx = target["startIndex"]
            end_idx = target["endIndex"] - 1  # keep the newline
            requests = []
            if end_idx > start_idx:
                requests.append({
                    "deleteContentRange": {
                        "range": {"startIndex": start_idx, "endIndex": end_idx}
                    }
                })
            requests.append({"insertText": {"location": {"index": start_idx}, "text": content}})

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown updateMode: {update_mode}",
            )

        try:
            batch_resp = await client.post(
                f"{DOCS_API_BASE}/{doc_id}:batchUpdate",
                headers=headers,
                json={"requests": requests},
            )
            batch_resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return {"success": True, "documentId": doc_id}


async def delete_document(token: str, params: dict[str, Any]) -> dict:
    """Move a Google Doc to trash via Drive API. Requires confirmed=True."""
    doc_id = params.get("documentId")
    confirmed = params.get("confirmed", False)

    if not doc_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documentId is required")
    if not confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="confirmed must be true to delete a document",
        )

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.delete(
                f"{DRIVE_API_BASE}/{doc_id}",
                headers=auth_headers(token),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return {"success": True, "documentId": doc_id, "message": "Document moved to trash"}


async def find_text_in_document(token: str, params: dict[str, Any]) -> dict:
    """Search for a text query inside a Google Doc's paragraphs."""
    doc_id = params.get("documentId")
    query = params.get("query", "")
    scope = params.get("scope", "all")
    para_index_filter = params.get("paragraphIndex")
    return_context = params.get("returnContext", False)

    if not doc_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="documentId is required")
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{DOCS_API_BASE}/{doc_id}", headers=auth_headers(token))
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    doc = resp.json()
    body_content = doc.get("body", {}).get("content", [])

    # Collect paragraphs with their text
    paragraphs: list[str] = []
    for element in body_content:
        if "paragraph" in element:
            text_parts = []
            for pel in element["paragraph"].get("elements", []):
                tr = pel.get("textRun", {})
                text_parts.append(tr.get("content", ""))
            paragraphs.append("".join(text_parts))

    query_lower = query.lower()
    matches = []

    def _search_paragraph(idx: int, text: str) -> None:
        text_lower = text.lower()
        start = 0
        while True:
            pos = text_lower.find(query_lower, start)
            if pos == -1:
                break
            match_end = pos + len(query)
            entry: dict[str, Any] = {
                "paragraphIndex": idx,
                "text": text,
                "matchStart": pos,
                "matchEnd": match_end,
            }
            if return_context:
                ctx_start = max(0, pos - 50)
                ctx_end = min(len(text), match_end + 50)
                entry["context"] = text[ctx_start:ctx_end]
            matches.append(entry)
            start = pos + 1  # look for next occurrence in same paragraph

    if scope == "indexed":
        if para_index_filter is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="paragraphIndex is required when scope is 'indexed'",
            )
        if para_index_filter < len(paragraphs):
            _search_paragraph(para_index_filter, paragraphs[para_index_filter])
    else:
        for i, text in enumerate(paragraphs):
            _search_paragraph(i, text)

    return {"matches": matches, "totalMatches": len(matches)}


# ──────────────────────────────────────────────
# Execute endpoint
# ──────────────────────────────────────────────


@router.post("/execute")
@limiter.limit("30/minute")
async def execute(
    request: Request,
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dispatch a Google Docs operation on behalf of the authenticated user."""
    credential = await get_user_credential(db, body.credentialId, current_user.id)
    token = await get_valid_access_token(credential, db)

    match body.operation:
        case "create":
            return await create_document(token, body.params)
        case "get":
            return await get_document(token, body.params)
        case "update":
            return await update_document(token, body.params)
        case "delete":
            return await delete_document(token, body.params)
        case "find_text":
            return await find_text_in_document(token, body.params)
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {body.operation}",
            )
