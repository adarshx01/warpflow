"""
Unified Google Workspace Service
=================================
Provides a single `GoogleWorkspaceService` class that wraps all five
Google API service modules (Sheets, Docs, Drive, Gmail, Forms) behind
one `execute(service, operation, params)` dispatch method.

Used by the direct workflow execution engine so any trigger type can
invoke a Google Workspace node without requiring an AI agent in the middle.
"""

from typing import Any

from app.services.google.google_sheets.router import (
    create_spreadsheet,
    get_spreadsheet,
    read_values,
    write_values,
    append_values,
    clear_values,
)
from app.services.google.google_docs.router import (
    create_document,
    get_document,
    update_document,
    delete_document,
    find_text_in_document,
)
from app.services.google.google_drive.router import (
    list_files,
    get_file,
    upload_file,
    download_file,
    delete_file,
    create_folder,
    share_file,
)
from app.services.google.gmail.router import (
    send_email,
    list_messages,
    get_message,
    search_messages,
    trash_message,
    list_labels,
)
from app.services.google.google_forms.router import (
    create_form,
    get_form,
    list_responses,
    get_response as get_form_response,
    update_form,
)


# ---------------------------------------------------------------------------
# Dispatch tables — map operation name → async function(token, params)
# ---------------------------------------------------------------------------

_SHEETS_OPS: dict[str, Any] = {
    "create":        create_spreadsheet,
    "get":           get_spreadsheet,
    "read_values":   read_values,
    "write_values":  write_values,
    "append_values": append_values,
    "clear_values":  clear_values,
}

_DOCS_OPS: dict[str, Any] = {
    "create":    create_document,
    "get":       get_document,
    "update":    update_document,
    "delete":    delete_document,
    "find_text": find_text_in_document,
}

_DRIVE_OPS: dict[str, Any] = {
    "list_files":    list_files,
    "get_file":      get_file,
    "upload_file":   upload_file,
    "download_file": download_file,
    "delete_file":   delete_file,
    "create_folder": create_folder,
    "share_file":    share_file,
}

_GMAIL_OPS: dict[str, Any] = {
    "send_email":      send_email,
    "list_messages":   list_messages,
    "get_message":     get_message,
    "search_messages": search_messages,
    "trash_message":   trash_message,
    "list_labels":     list_labels,
}

_FORMS_OPS: dict[str, Any] = {
    "create":         create_form,
    "get":            get_form,
    "list_responses": list_responses,
    "get_response":   get_form_response,
    "update":         update_form,
}

# Maps frontend node `type` → operation dispatch table
_SERVICE_REGISTRY: dict[str, dict[str, Any]] = {
    "google-sheets": _SHEETS_OPS,
    "google-docs":   _DOCS_OPS,
    "google-drive":  _DRIVE_OPS,
    "gmail":         _GMAIL_OPS,
    "google-forms":  _FORMS_OPS,
}

# All Google Workspace node types recognised by this service
GOOGLE_NODE_TYPES: frozenset[str] = frozenset(_SERVICE_REGISTRY.keys())


class GoogleWorkspaceService:
    """
    Unified dispatcher for all Google Workspace API operations.

    Parameters
    ----------
    token : str
        A valid OAuth2 access token for the authenticated user.

    Example
    -------
    >>> svc = GoogleWorkspaceService(token)
    >>> result = await svc.execute("google-sheets", "read_values",
    ...                            {"spreadsheetId": "abc", "range": "Sheet1!A1:D10"})
    """

    def __init__(self, token: str) -> None:
        self._token = token

    async def execute(
        self,
        service: str,
        operation: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Dispatch an operation to the appropriate Google API helper.

        Parameters
        ----------
        service : str
            Google Workspace node type, e.g. ``"google-sheets"``, ``"gmail"``.
        operation : str
            Operation name as stored in node.data.operation, e.g.
            ``"read_values"``, ``"send_email"``.
        params : dict
            Operation-specific parameters from node.data.params.

        Returns
        -------
        dict
            The API response.

        Raises
        ------
        ValueError
            If the service or operation is unknown.
        """
        ops = _SERVICE_REGISTRY.get(service)
        if ops is None:
            raise ValueError(
                f"Unknown Google Workspace service: '{service}'. "
                f"Valid services: {sorted(_SERVICE_REGISTRY)}"
            )

        fn = ops.get(operation)
        if fn is None:
            raise ValueError(
                f"Unknown operation '{operation}' for service '{service}'. "
                f"Valid operations: {sorted(ops)}"
            )

        return await fn(self._token, params)

    # ── Convenience wrappers (optional, for direct use) ──────────────────

    # Google Sheets
    async def sheets_create(self, params: dict) -> dict:
        return await create_spreadsheet(self._token, params)

    async def sheets_get(self, params: dict) -> dict:
        return await get_spreadsheet(self._token, params)

    async def sheets_read_values(self, params: dict) -> dict:
        return await read_values(self._token, params)

    async def sheets_write_values(self, params: dict) -> dict:
        return await write_values(self._token, params)

    async def sheets_append_values(self, params: dict) -> dict:
        return await append_values(self._token, params)

    async def sheets_clear_values(self, params: dict) -> dict:
        return await clear_values(self._token, params)

    # Google Docs
    async def docs_create(self, params: dict) -> dict:
        return await create_document(self._token, params)

    async def docs_get(self, params: dict) -> dict:
        return await get_document(self._token, params)

    async def docs_update(self, params: dict) -> dict:
        return await update_document(self._token, params)

    async def docs_delete(self, params: dict) -> dict:
        return await delete_document(self._token, params)

    async def docs_find_text(self, params: dict) -> dict:
        return await find_text_in_document(self._token, params)

    # Google Drive
    async def drive_list_files(self, params: dict) -> dict:
        return await list_files(self._token, params)

    async def drive_get_file(self, params: dict) -> dict:
        return await get_file(self._token, params)

    async def drive_upload_file(self, params: dict) -> dict:
        return await upload_file(self._token, params)

    async def drive_download_file(self, params: dict) -> dict:
        return await download_file(self._token, params)

    async def drive_delete_file(self, params: dict) -> dict:
        return await delete_file(self._token, params)

    async def drive_create_folder(self, params: dict) -> dict:
        return await create_folder(self._token, params)

    async def drive_share_file(self, params: dict) -> dict:
        return await share_file(self._token, params)

    # Gmail
    async def gmail_send_email(self, params: dict) -> dict:
        return await send_email(self._token, params)

    async def gmail_list_messages(self, params: dict) -> dict:
        return await list_messages(self._token, params)

    async def gmail_get_message(self, params: dict) -> dict:
        return await get_message(self._token, params)

    async def gmail_search_messages(self, params: dict) -> dict:
        return await search_messages(self._token, params)

    async def gmail_trash_message(self, params: dict) -> dict:
        return await trash_message(self._token, params)

    async def gmail_list_labels(self, params: dict) -> dict:
        return await list_labels(self._token, params)

    # Google Forms
    async def forms_create(self, params: dict) -> dict:
        return await create_form(self._token, params)

    async def forms_get(self, params: dict) -> dict:
        return await get_form(self._token, params)

    async def forms_list_responses(self, params: dict) -> dict:
        return await list_responses(self._token, params)

    async def forms_get_response(self, params: dict) -> dict:
        return await get_form_response(self._token, params)

    async def forms_update(self, params: dict) -> dict:
        return await update_form(self._token, params)
