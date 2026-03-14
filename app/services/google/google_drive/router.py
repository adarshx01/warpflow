"""
Google Drive router: OAuth2 flow + execute endpoint for Drive API v3.
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
from app.services.google.google_drive.schemas import DriveExecuteRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-drive", tags=["google-drive"])

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"
REDIRECT_URI = "http://localhost:8000/api/google-drive/oauth/callback"
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


# ── Drive API helpers ────────────────────────

async def list_files(token: str, params: dict[str, Any]) -> dict:
    """List files in Google Drive."""
    query = params.get("query", "")
    page_size = min(params.get("pageSize", 20), 100)
    page_token = params.get("pageToken")
    folder_id = params.get("folderId")

    q_parts = []
    if query:
        q_parts.append(f"name contains '{query}'")
    if folder_id:
        q_parts.append(f"'{folder_id}' in parents")
    q_parts.append("trashed = false")

    api_params: dict[str, Any] = {
        "pageSize": page_size,
        "fields": "nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink, iconLink, parents)",
        "orderBy": "modifiedTime desc",
    }
    if q_parts:
        api_params["q"] = " and ".join(q_parts)
    if page_token:
        api_params["pageToken"] = page_token

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{DRIVE_API_BASE}/files",
                headers=auth_headers(token),
                params=api_params,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return resp.json()


async def get_file(token: str, params: dict[str, Any]) -> dict:
    """Get file metadata."""
    file_id = params.get("fileId")
    if not file_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fileId is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{DRIVE_API_BASE}/files/{file_id}",
                headers=auth_headers(token),
                params={"fields": "id, name, mimeType, size, createdTime, modifiedTime, webViewLink, parents, permissions"},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return resp.json()


async def upload_file(token: str, params: dict[str, Any]) -> dict:
    """Create/upload a file with text content."""
    name = params.get("name", "Untitled")
    content = params.get("content", "")
    mime_type = params.get("mimeType", "text/plain")
    folder_id = params.get("folderId")

    metadata: dict[str, Any] = {"name": name, "mimeType": mime_type}
    if folder_id:
        metadata["parents"] = [folder_id]

    headers = auth_headers(token)

    async with httpx.AsyncClient() as client:
        # Multipart upload
        try:
            resp = await client.post(
                f"{DRIVE_UPLOAD_BASE}/files",
                headers={**headers, "Content-Type": "application/json"},
                params={"uploadType": "multipart"},
                json=metadata,
            )
            # For simple metadata-only creation, then update content
            resp_meta = await client.post(
                f"{DRIVE_API_BASE}/files",
                headers=headers,
                json=metadata,
            )
            resp_meta.raise_for_status()
            file_data = resp_meta.json()
            file_id = file_data["id"]

            if content:
                resp_content = await client.patch(
                    f"{DRIVE_UPLOAD_BASE}/files/{file_id}",
                    headers={**headers, "Content-Type": mime_type},
                    params={"uploadType": "media"},
                    content=content.encode("utf-8"),
                )
                resp_content.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return {
        "fileId": file_id,
        "name": name,
        "webViewLink": file_data.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view"),
    }


async def download_file(token: str, params: dict[str, Any]) -> dict:
    """Download/export file content."""
    file_id = params.get("fileId")
    export_mime = params.get("exportMimeType", "text/plain")
    if not file_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fileId is required")

    async with httpx.AsyncClient() as client:
        # First get file metadata to check type
        try:
            meta_resp = await client.get(
                f"{DRIVE_API_BASE}/files/{file_id}",
                headers=auth_headers(token),
                params={"fields": "mimeType, name"},
            )
            meta_resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

        meta = meta_resp.json()
        mime = meta.get("mimeType", "")

        try:
            if mime.startswith("application/vnd.google-apps."):
                # Google Workspace file → export
                resp = await client.get(
                    f"{DRIVE_API_BASE}/files/{file_id}/export",
                    headers=auth_headers(token),
                    params={"mimeType": export_mime},
                )
            else:
                # Binary file → download
                resp = await client.get(
                    f"{DRIVE_API_BASE}/files/{file_id}",
                    headers=auth_headers(token),
                    params={"alt": "media"},
                )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return {
        "fileName": meta.get("name"),
        "mimeType": mime,
        "content": resp.text[:50000],  # Cap at 50KB text
    }


async def delete_file(token: str, params: dict[str, Any]) -> dict:
    """Trash a file."""
    file_id = params.get("fileId")
    if not file_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fileId is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.patch(
                f"{DRIVE_API_BASE}/files/{file_id}",
                headers=auth_headers(token),
                json={"trashed": True},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return {"success": True, "fileId": file_id, "message": "File moved to trash"}


async def create_folder(token: str, params: dict[str, Any]) -> dict:
    """Create a folder in Google Drive."""
    name = params.get("name", "New Folder")
    parent_id = params.get("parentId")

    metadata: dict[str, Any] = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{DRIVE_API_BASE}/files",
                headers=auth_headers(token),
                json=metadata,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    folder = resp.json()
    return {
        "folderId": folder["id"],
        "name": name,
        "webViewLink": folder.get("webViewLink", f"https://drive.google.com/drive/folders/{folder['id']}"),
    }


async def share_file(token: str, params: dict[str, Any]) -> dict:
    """Share a file with a user or make it public."""
    file_id = params.get("fileId")
    role = params.get("role", "reader")  # reader, writer, commenter
    email = params.get("email")
    share_type = params.get("type", "user")  # user, anyone

    if not file_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="fileId is required")

    permission: dict[str, Any] = {"role": role, "type": share_type}
    if share_type == "user":
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email is required for user sharing")
        permission["emailAddress"] = email

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{DRIVE_API_BASE}/files/{file_id}/permissions",
                headers=auth_headers(token),
                json=permission,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return {"success": True, "fileId": file_id, "permission": resp.json()}


# ── Execute endpoint ─────────────────────────

@router.post("/execute")
@limiter.limit("30/minute")
async def execute(
    request: Request,
    body: DriveExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    credential = await get_user_credential(db, body.credentialId, current_user.id)
    token = await get_valid_access_token(credential, db)

    match body.operation:
        case "list_files":
            return await list_files(token, body.params)
        case "get_file":
            return await get_file(token, body.params)
        case "upload_file":
            return await upload_file(token, body.params)
        case "download_file":
            return await download_file(token, body.params)
        case "delete_file":
            return await delete_file(token, body.params)
        case "create_folder":
            return await create_folder(token, body.params)
        case "share_file":
            return await share_file(token, body.params)
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {body.operation}",
            )
