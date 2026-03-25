"""
Google Forms router: OAuth2 flow + execute endpoint for Forms API v1.
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
from app.services.google.google_forms.schemas import FormsExecuteRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google-forms", tags=["google-forms"])

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
]
FORMS_API_BASE = "https://forms.googleapis.com/v1/forms"
REDIRECT_URI = "http://localhost:8000/api/google-forms/oauth/callback"
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


# ── Forms API helpers ────────────────────────

async def create_form(token: str, params: dict[str, Any]) -> dict:
    """Create a new Google Form."""
    title = params.get("title", "Untitled Form")
    description = params.get("description", "")

    body: dict[str, Any] = {
        "info": {"title": title, "documentTitle": title},
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                FORMS_API_BASE,
                headers=auth_headers(token),
                json=body,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

        form = resp.json()
        form_id = form["formId"]

        # Add description and questions via batchUpdate if provided
        requests = []
        if description:
            requests.append({
                "updateFormInfo": {
                    "info": {"description": description},
                    "updateMask": "description",
                }
            })

        questions = params.get("questions", [])
        for i, q in enumerate(questions):
            q_body: dict[str, Any] = {
                "required": q.get("required", False),
                "title": q.get("title", f"Question {i + 1}"),
            }
            q_type = q.get("type", "text")
            if q_type == "text":
                q_body["textQuestion"] = {"paragraph": q.get("paragraph", False)}
            elif q_type == "choice":
                options = [{"value": opt} for opt in q.get("options", ["Option 1"])]
                q_body["choiceQuestion"] = {
                    "type": q.get("choiceType", "RADIO"),
                    "options": options,
                }
            elif q_type == "scale":
                q_body["scaleQuestion"] = {
                    "low": q.get("low", 1),
                    "high": q.get("high", 5),
                    "lowLabel": q.get("lowLabel", ""),
                    "highLabel": q.get("highLabel", ""),
                }

            requests.append({
                "createItem": {
                    "item": {
                        "title": q.get("title", f"Question {i + 1}"),
                        "questionItem": {"question": q_body},
                    },
                    "location": {"index": i},
                }
            })

        if requests:
            try:
                batch_resp = await client.post(
                    f"{FORMS_API_BASE}/{form_id}:batchUpdate",
                    headers=auth_headers(token),
                    json={"requests": requests},
                )
                batch_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                await handle_google_error(exc)

    return {
        "formId": form_id,
        "title": title,
        "responderUri": form.get("responderUri"),
        "editUrl": f"https://docs.google.com/forms/d/{form_id}/edit",
    }


async def get_form(token: str, params: dict[str, Any]) -> dict:
    """Get form details."""
    form_id = params.get("formId")
    if not form_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="formId is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{FORMS_API_BASE}/{form_id}",
                headers=auth_headers(token),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    form = resp.json()
    items = []
    for item in form.get("items", []):
        item_data: dict[str, Any] = {
            "itemId": item.get("itemId"),
            "title": item.get("title"),
        }
        if "questionItem" in item:
            q = item["questionItem"].get("question", {})
            item_data["required"] = q.get("required", False)
            if "textQuestion" in q:
                item_data["type"] = "text"
            elif "choiceQuestion" in q:
                item_data["type"] = "choice"
                item_data["options"] = [o.get("value") for o in q["choiceQuestion"].get("options", [])]
            elif "scaleQuestion" in q:
                item_data["type"] = "scale"
        items.append(item_data)

    return {
        "formId": form["formId"],
        "title": form.get("info", {}).get("title"),
        "description": form.get("info", {}).get("description"),
        "responderUri": form.get("responderUri"),
        "items": items,
    }


async def list_responses(token: str, params: dict[str, Any]) -> dict:
    """List form responses."""
    form_id = params.get("formId")
    if not form_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="formId is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{FORMS_API_BASE}/{form_id}/responses",
                headers=auth_headers(token),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    data = resp.json()
    responses = []
    for r in data.get("responses", []):
        answers = {}
        for qid, answer in r.get("answers", {}).items():
            text_answers = answer.get("textAnswers", {}).get("answers", [])
            answers[qid] = [a.get("value", "") for a in text_answers]
        responses.append({
            "responseId": r.get("responseId"),
            "createTime": r.get("createTime"),
            "lastSubmittedTime": r.get("lastSubmittedTime"),
            "respondentEmail": r.get("respondentEmail"),
            "answers": answers,
        })

    return {"responses": responses, "totalResponses": len(responses)}


async def get_response(token: str, params: dict[str, Any]) -> dict:
    """Get a single form response."""
    form_id = params.get("formId")
    response_id = params.get("responseId")
    if not form_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="formId is required")
    if not response_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="responseId is required")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{FORMS_API_BASE}/{form_id}/responses/{response_id}",
                headers=auth_headers(token),
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    r = resp.json()
    answers = {}
    for qid, answer in r.get("answers", {}).items():
        text_answers = answer.get("textAnswers", {}).get("answers", [])
        answers[qid] = [a.get("value", "") for a in text_answers]

    return {
        "responseId": r.get("responseId"),
        "createTime": r.get("createTime"),
        "lastSubmittedTime": r.get("lastSubmittedTime"),
        "respondentEmail": r.get("respondentEmail"),
        "answers": answers,
    }


async def update_form(token: str, params: dict[str, Any]) -> dict:
    """Update form via batchUpdate (add questions, update info)."""
    form_id = params.get("formId")
    if not form_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="formId is required")

    requests = []

    new_title = params.get("title")
    new_description = params.get("description")
    if new_title or new_description:
        info: dict[str, Any] = {}
        mask_parts = []
        if new_title:
            info["title"] = new_title
            mask_parts.append("title")
        if new_description:
            info["description"] = new_description
            mask_parts.append("description")
        requests.append({
            "updateFormInfo": {
                "info": info,
                "updateMask": ",".join(mask_parts),
            }
        })

    if not requests:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{FORMS_API_BASE}/{form_id}:batchUpdate",
                headers=auth_headers(token),
                json={"requests": requests},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            await handle_google_error(exc)

    return {"success": True, "formId": form_id}


# ── Execute endpoint ─────────────────────────

@router.post("/execute")
@limiter.limit("30/minute")
async def execute(
    request: Request,
    body: FormsExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    credential = await get_user_credential(db, body.credentialId, current_user.id)
    token = await get_valid_access_token(credential, db)

    match body.operation:
        case "create":
            return await create_form(token, body.params)
        case "get":
            return await get_form(token, body.params)
        case "list_responses":
            return await list_responses(token, body.params)
        case "get_response":
            return await get_response(token, body.params)
        case "update":
            return await update_form(token, body.params)
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown operation: {body.operation}",
            )
