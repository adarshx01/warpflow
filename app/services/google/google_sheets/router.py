"""
Google Sheets router: OAuth2 flow + execute endpoint for Sheets API v4.
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
from app.services.google.google_sheets.schemas import SheetsExecuteRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-sheets", tags=["google-sheets"])

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]
SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
REDIRECT_URI = "http://localhost:8000/api/google-sheets/oauth/callback"
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


# ── Sheets API helpers ───────────────────────

async def create_spreadsheet(token: str, params: dict[str, Any]) -> dict:
    """Create a new Google Spreadsheet."""
    title = params.get("title", "Untitled Spreadsheet")
    sheet_names = params.get("sheetNames", ["Sheet1"])

    body: dict[str, Any] = {
        "properties": {"title": title},
        "sheets": [{"properties": {"title": name}} for name in sheet_names],
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                SHEETS_API_BASE,
                headers=auth_headers(token),
                json=body,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    data = resp.json()
    return {
        "spreadsheetId": data["spreadsheetId"],
        "title": data["properties"]["title"],
        "url": data["spreadsheetUrl"],
        "sheets": [s["properties"]["title"] for s in data.get("sheets", [])],
    }


async def get_spreadsheet(token: str, params: dict[str, Any]) -> dict:
    """Get spreadsheet metadata."""
    spreadsheet_id = params.get("spreadsheetId")
    if not spreadsheet_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="spreadsheetId is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{SHEETS_API_BASE}/{spreadsheet_id}",
                headers=auth_headers(token),
                params={"fields": "spreadsheetId,properties.title,spreadsheetUrl,sheets.properties"},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    data = resp.json()
    return {
        "spreadsheetId": data["spreadsheetId"],
        "title": data["properties"]["title"],
        "url": data["spreadsheetUrl"],
        "sheets": [
            {
                "sheetId": s["properties"]["sheetId"],
                "title": s["properties"]["title"],
                "rowCount": s["properties"].get("gridProperties", {}).get("rowCount"),
                "columnCount": s["properties"].get("gridProperties", {}).get("columnCount"),
            }
            for s in data.get("sheets", [])
        ],
    }


async def read_values(token: str, params: dict[str, Any]) -> dict:
    """Read values from a range (e.g. 'Sheet1!A1:D10')."""
    spreadsheet_id = params.get("spreadsheetId")
    range_str = params.get("range", "Sheet1")
    if not spreadsheet_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="spreadsheetId is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_str}",
                headers=auth_headers(token),
                params={"valueRenderOption": "FORMATTED_VALUE"},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    data = resp.json()
    return {
        "range": data.get("range"),
        "values": data.get("values", []),
        "majorDimension": data.get("majorDimension", "ROWS"),
    }


async def write_values(token: str, params: dict[str, Any]) -> dict:
    """Write values to a range."""
    spreadsheet_id = params.get("spreadsheetId")
    range_str = params.get("range", "Sheet1!A1")
    values = params.get("values", [])
    if not spreadsheet_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="spreadsheetId is required")
    if not values:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="values is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.put(
                f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_str}",
                headers=auth_headers(token),
                params={"valueInputOption": "USER_ENTERED"},
                json={
                    "range": range_str,
                    "majorDimension": "ROWS",
                    "values": values,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    data = resp.json()
    return {
        "updatedRange": data.get("updatedRange"),
        "updatedRows": data.get("updatedRows"),
        "updatedColumns": data.get("updatedColumns"),
        "updatedCells": data.get("updatedCells"),
    }


async def append_values(token: str, params: dict[str, Any]) -> dict:
    """Append values to the end of a range."""
    spreadsheet_id = params.get("spreadsheetId")
    range_str = params.get("range", "Sheet1")
    values = params.get("values", [])
    if not spreadsheet_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="spreadsheetId is required")
    if not values:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="values is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_str}:append",
                headers=auth_headers(token),
                params={
                    "valueInputOption": "USER_ENTERED",
                    "insertDataOption": "INSERT_ROWS",
                },
                json={
                    "range": range_str,
                    "majorDimension": "ROWS",
                    "values": values,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    data = resp.json()
    updates = data.get("updates", {})
    return {
        "updatedRange": updates.get("updatedRange"),
        "updatedRows": updates.get("updatedRows"),
        "updatedColumns": updates.get("updatedColumns"),
        "updatedCells": updates.get("updatedCells"),
    }


async def clear_values(token: str, params: dict[str, Any]) -> dict:
    """Clear values from a range."""
    spreadsheet_id = params.get("spreadsheetId")
    range_str = params.get("range", "Sheet1")
    if not spreadsheet_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="spreadsheetId is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{range_str}:clear",
                headers=auth_headers(token),
                json={},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    data = resp.json()
    return {
        "clearedRange": data.get("clearedRange"),
        "spreadsheetId": data.get("spreadsheetId"),
    }


# ── Execute endpoint ─────────────────────────

@router.post("/execute")
@limiter.limit("30/minute")
async def execute(
    request: Request,
    body: SheetsExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    credential = await get_user_credential(db, body.credentialId, current_user.id)
    token = await get_valid_access_token(credential, db)

    match body.operation:
        case "create":
            return await create_spreadsheet(token, body.params)
        case "get":
            return await get_spreadsheet(token, body.params)
        case "read_values":
            return await read_values(token, body.params)
        case "write_values":
            return await write_values(token, body.params)
        case "append_values":
            return await append_values(token, body.params)
        case "clear_values":
            return await clear_values(token, body.params)
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {body.operation}",
            )
