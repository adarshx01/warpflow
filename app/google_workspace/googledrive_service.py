"""Google Drive execute logic."""
import httpx
from fastapi import HTTPException


DRIVE_BASE = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"


async def execute(access_token: str, operation: str, params: dict) -> dict:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        if operation == "list":
            q = params.get("query", "")
            page_size = params.get("pageSize", 10)
            resp = await client.get(
                f"{DRIVE_BASE}?q={q}&pageSize={page_size}&fields=files(id,name,mimeType,modifiedTime)",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

        elif operation == "get":
            file_id = params.get("fileId", "")
            resp = await client.get(
                f"{DRIVE_BASE}/{file_id}?fields=id,name,mimeType,size,modifiedTime,parents",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

        elif operation == "delete":
            file_id = params.get("fileId", "")
            resp = await client.delete(f"{DRIVE_BASE}/{file_id}", headers=headers)
            resp.raise_for_status()
            return {"deleted": file_id}

        elif operation == "create_folder":
            body = {
                "name": params.get("name", "New Folder"),
                "mimeType": "application/vnd.google-apps.folder",
            }
            if params.get("parentId"):
                body["parents"] = [params["parentId"]]
            resp = await client.post(DRIVE_BASE, headers=headers, json=body)
            resp.raise_for_status()
            return resp.json()

        elif operation == "move":
            file_id = params.get("fileId", "")
            new_parent = params.get("newParentId", "")
            # Get current parents first
            info = await client.get(f"{DRIVE_BASE}/{file_id}?fields=parents", headers=headers)
            info.raise_for_status()
            old_parents = ",".join(info.json().get("parents", []))
            resp = await client.patch(
                f"{DRIVE_BASE}/{file_id}?addParents={new_parent}&removeParents={old_parents}&fields=id,parents",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

        else:
            raise HTTPException(status_code=400, detail=f"Unknown Google Drive operation: {operation}")
