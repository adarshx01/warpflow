"""Google Sheets execute logic."""
import httpx
from fastapi import HTTPException


SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


async def execute(access_token: str, operation: str, params: dict) -> dict:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        if operation == "read":
            sheet_id = params.get("spreadsheetId", "")
            range_ = params.get("range", "Sheet1")
            resp = await client.get(
                f"{SHEETS_BASE}/{sheet_id}/values/{range_}", headers=headers
            )
            resp.raise_for_status()
            return resp.json()

        elif operation == "write":
            sheet_id = params.get("spreadsheetId", "")
            range_ = params.get("range", "Sheet1")
            values = params.get("values", [])
            resp = await client.put(
                f"{SHEETS_BASE}/{sheet_id}/values/{range_}?valueInputOption=USER_ENTERED",
                headers=headers,
                json={"values": values},
            )
            resp.raise_for_status()
            return resp.json()

        elif operation == "append":
            sheet_id = params.get("spreadsheetId", "")
            range_ = params.get("range", "Sheet1")
            values = params.get("values", [])
            resp = await client.post(
                f"{SHEETS_BASE}/{sheet_id}/values/{range_}:append?valueInputOption=USER_ENTERED",
                headers=headers,
                json={"values": values},
            )
            resp.raise_for_status()
            return resp.json()

        elif operation == "create":
            title = params.get("title", "New Spreadsheet")
            resp = await client.post(
                SHEETS_BASE,
                headers=headers,
                json={"properties": {"title": title}},
            )
            resp.raise_for_status()
            return resp.json()

        elif operation == "clear":
            sheet_id = params.get("spreadsheetId", "")
            range_ = params.get("range", "Sheet1")
            resp = await client.post(
                f"{SHEETS_BASE}/{sheet_id}/values/{range_}:clear", headers=headers
            )
            resp.raise_for_status()
            return resp.json()

        else:
            raise HTTPException(status_code=400, detail=f"Unknown Google Sheets operation: {operation}")
