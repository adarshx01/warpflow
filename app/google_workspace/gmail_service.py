"""Gmail execute logic."""
import httpx
from fastapi import HTTPException


async def execute(access_token: str, operation: str, params: dict) -> dict:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    if operation == "send":
        import base64
        from email.mime.text import MIMEText
        msg = MIMEText(params.get("body", ""))
        msg["To"] = params.get("to", "")
        msg["Subject"] = params.get("subject", "")
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers=headers,
                json={"raw": raw},
            )
            resp.raise_for_status()
            return resp.json()

    elif operation == "list":
        q = params.get("query", "")
        max_results = params.get("maxResults", 10)
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={q}&maxResults={max_results}",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    elif operation == "get":
        msg_id = params.get("messageId", "")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    else:
        raise HTTPException(status_code=400, detail=f"Unknown Gmail operation: {operation}")
