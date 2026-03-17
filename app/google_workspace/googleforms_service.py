"""Google Forms execute logic."""
import httpx
from fastapi import HTTPException


FORMS_BASE = "https://forms.googleapis.com/v1/forms"


async def execute(access_token: str, operation: str, params: dict) -> dict:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        if operation == "get":
            form_id = params.get("formId", "")
            resp = await client.get(f"{FORMS_BASE}/{form_id}", headers=headers)
            resp.raise_for_status()
            return resp.json()

        elif operation == "list_responses":
            form_id = params.get("formId", "")
            resp = await client.get(f"{FORMS_BASE}/{form_id}/responses", headers=headers)
            resp.raise_for_status()
            return resp.json()

        elif operation == "create":
            body = {"info": {"title": params.get("title", "New Form")}}
            resp = await client.post(FORMS_BASE, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()

        else:
            raise HTTPException(status_code=400, detail=f"Unknown Google Forms operation: {operation}")
