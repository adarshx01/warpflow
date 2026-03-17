"""Google Docs execute logic."""
import httpx
from fastapi import HTTPException


DOCS_BASE = "https://docs.googleapis.com/v1/documents"
DRIVE_BASE = "https://www.googleapis.com/drive/v3/files"


async def execute(access_token: str, operation: str, params: dict) -> dict:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        if operation == "create":
            # Create document
            resp = await client.post(
                DOCS_BASE, headers=headers, json={"title": params.get("title", "Untitled")}
            )
            resp.raise_for_status()
            doc = resp.json()
            doc_id = doc["documentId"]

            # Insert initial content if provided
            content = params.get("content", "")
            if content:
                requests = [{"insertText": {"location": {"index": 1}, "text": content}}]
                r2 = await client.post(
                    f"{DOCS_BASE}/{doc_id}:batchUpdate",
                    headers=headers,
                    json={"requests": requests},
                )
                r2.raise_for_status()
            return doc

        elif operation == "get":
            doc_id = params.get("documentId", "")
            resp = await client.get(f"{DOCS_BASE}/{doc_id}", headers=headers)
            resp.raise_for_status()
            return resp.json()

        elif operation == "update":
            doc_id = params.get("documentId", "")
            mode = params.get("updateMode", "append")
            content = params.get("content", "")

            if mode == "append":
                # Get current doc to find end index
                doc_resp = await client.get(f"{DOCS_BASE}/{doc_id}", headers=headers)
                doc_resp.raise_for_status()
                body = doc_resp.json().get("body", {})
                end_index = body.get("content", [{}])[-1].get("endIndex", 1) - 1
                requests = [{"insertText": {"location": {"index": end_index}, "text": content}}]
            elif mode == "replace_body":
                requests = [
                    {"deleteContentRange": {"range": {"startIndex": 1, "endIndex": 1}}},
                    {"insertText": {"location": {"index": 1}, "text": content}},
                ]
            elif mode == "by_index":
                idx = params.get("paragraphIndex", 0)
                requests = [{"insertText": {"location": {"index": idx}, "text": content}}]
            else:
                raise HTTPException(status_code=400, detail=f"Unknown updateMode: {mode}")

            resp = await client.post(
                f"{DOCS_BASE}/{doc_id}:batchUpdate",
                headers=headers,
                json={"requests": requests},
            )
            resp.raise_for_status()
            return resp.json()

        elif operation == "delete":
            doc_id = params.get("documentId", "")
            resp = await client.delete(f"{DRIVE_BASE}/{doc_id}", headers=headers)
            resp.raise_for_status()
            return {"deleted": doc_id}

        elif operation == "find_text":
            doc_id = params.get("documentId", "")
            query = params.get("query", "").lower()
            resp = await client.get(f"{DOCS_BASE}/{doc_id}", headers=headers)
            resp.raise_for_status()
            doc = resp.json()
            matches = []
            for element in doc.get("body", {}).get("content", []):
                para = element.get("paragraph")
                if not para:
                    continue
                text = "".join(
                    e.get("textRun", {}).get("content", "")
                    for e in para.get("elements", [])
                )
                if query in text.lower():
                    matches.append(text.strip())
            return {"matches": matches, "count": len(matches)}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown Google Docs operation: {operation}")
