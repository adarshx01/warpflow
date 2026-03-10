"""
Service tool definitions for the AI agent.
Maps service node types to their available operations and function references.
"""

from typing import Any, Callable, Awaitable

from app.services.google.google_docs.router import (
    create_document, get_document, update_document,
    delete_document, find_text_in_document,
)
from app.services.google.google_drive.router import (
    list_files, get_file, upload_file, download_file,
    delete_file, create_folder, share_file,
)
from app.services.google.gmail.router import (
    send_email, list_messages, get_message,
    search_messages, trash_message, list_labels,
)
from app.services.google.google_sheets.router import (
    create_spreadsheet, get_spreadsheet, read_values,
    write_values, append_values, clear_values,
)
from app.services.google.google_forms.router import (
    create_form, get_form, list_responses,
    get_response as get_form_response, update_form,
)

ServiceFn = Callable[[str, dict[str, Any]], Awaitable[dict]]


# Wrapper for auto-confirming destructive operations
async def _delete_document_confirmed(token: str, params: dict[str, Any]) -> dict:
    return await delete_document(token, {**params, "confirmed": True})


# ─────────────────────────────────────────────
# Tool Registry
# Each service type maps to a list of tool definitions.
# _fn: the async function to call with (token, params)
# ─────────────────────────────────────────────

TOOL_REGISTRY: dict[str, list[dict[str, Any]]] = {
    "google-docs": [
        {
            "name": "google_docs_create",
            "description": "Create a new Google Docs document with optional initial content",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Initial content for the document"},
                },
                "required": ["title"],
            },
            "_fn": create_document,
        },
        {
            "name": "google_docs_get",
            "description": "Get the content and metadata of a Google Docs document",
            "parameters": {
                "type": "object",
                "properties": {
                    "documentId": {"type": "string", "description": "The Google Docs document ID"},
                },
                "required": ["documentId"],
            },
            "_fn": get_document,
        },
        {
            "name": "google_docs_update",
            "description": "Update content in a Google Docs document",
            "parameters": {
                "type": "object",
                "properties": {
                    "documentId": {"type": "string", "description": "The document ID"},
                    "content": {"type": "string", "description": "The new content to write"},
                    "updateMode": {
                        "type": "string",
                        "enum": ["replace_body", "append", "by_index"],
                        "description": "How to update: replace_body (replace all content), append (add to end), by_index (insert at paragraph index)",
                    },
                },
                "required": ["documentId", "content", "updateMode"],
            },
            "_fn": update_document,
        },
        {
            "name": "google_docs_delete",
            "description": "Delete (trash) a Google Docs document",
            "parameters": {
                "type": "object",
                "properties": {
                    "documentId": {"type": "string", "description": "The document ID to delete"},
                },
                "required": ["documentId"],
            },
            "_fn": _delete_document_confirmed,
        },
        {
            "name": "google_docs_find_text",
            "description": "Search for text within a Google Docs document",
            "parameters": {
                "type": "object",
                "properties": {
                    "documentId": {"type": "string", "description": "The document ID to search in"},
                    "query": {"type": "string", "description": "Text to search for"},
                    "returnContext": {"type": "boolean", "description": "Whether to return surrounding text context"},
                },
                "required": ["documentId", "query"],
            },
            "_fn": find_text_in_document,
        },
    ],
    "google-drive": [
        {
            "name": "google_drive_list_files",
            "description": "List files in Google Drive, optionally filtered by query or folder",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query to filter files by name"},
                    "pageSize": {"type": "integer", "description": "Number of files to return (max 100)"},
                    "folderId": {"type": "string", "description": "Folder ID to list files from"},
                },
                "required": [],
            },
            "_fn": list_files,
        },
        {
            "name": "google_drive_get_file",
            "description": "Get metadata of a specific file in Google Drive",
            "parameters": {
                "type": "object",
                "properties": {
                    "fileId": {"type": "string", "description": "The file ID"},
                },
                "required": ["fileId"],
            },
            "_fn": get_file,
        },
        {
            "name": "google_drive_upload_file",
            "description": "Create and upload a text file to Google Drive",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "File name"},
                    "content": {"type": "string", "description": "File content"},
                    "mimeType": {"type": "string", "description": "MIME type (default: text/plain)"},
                    "folderId": {"type": "string", "description": "Parent folder ID"},
                },
                "required": ["name", "content"],
            },
            "_fn": upload_file,
        },
        {
            "name": "google_drive_download_file",
            "description": "Download or export file content from Google Drive",
            "parameters": {
                "type": "object",
                "properties": {
                    "fileId": {"type": "string", "description": "The file ID to download"},
                    "exportMimeType": {"type": "string", "description": "Export format for Google Workspace files (default: text/plain)"},
                },
                "required": ["fileId"],
            },
            "_fn": download_file,
        },
        {
            "name": "google_drive_delete_file",
            "description": "Move a file to trash in Google Drive",
            "parameters": {
                "type": "object",
                "properties": {
                    "fileId": {"type": "string", "description": "The file ID to delete"},
                },
                "required": ["fileId"],
            },
            "_fn": delete_file,
        },
        {
            "name": "google_drive_create_folder",
            "description": "Create a new folder in Google Drive",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Folder name"},
                    "parentId": {"type": "string", "description": "Parent folder ID"},
                },
                "required": ["name"],
            },
            "_fn": create_folder,
        },
        {
            "name": "google_drive_share_file",
            "description": "Share a Google Drive file with a user or make it public",
            "parameters": {
                "type": "object",
                "properties": {
                    "fileId": {"type": "string", "description": "The file ID to share"},
                    "role": {"type": "string", "enum": ["reader", "writer", "commenter"], "description": "Permission role"},
                    "email": {"type": "string", "description": "Email address to share with (required for user type)"},
                    "type": {"type": "string", "enum": ["user", "anyone"], "description": "Share type"},
                },
                "required": ["fileId", "role", "type"],
            },
            "_fn": share_file,
        },
    ],
    "gmail": [
        {
            "name": "gmail_send_email",
            "description": "Send an email via Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body (plain text)"},
                    "bodyHtml": {"type": "string", "description": "Email body (HTML, optional)"},
                    "cc": {"type": "string", "description": "CC recipients"},
                    "bcc": {"type": "string", "description": "BCC recipients"},
                },
                "required": ["to", "subject", "body"],
            },
            "_fn": send_email,
        },
        {
            "name": "gmail_list_messages",
            "description": "List recent messages from the Gmail inbox",
            "parameters": {
                "type": "object",
                "properties": {
                    "maxResults": {"type": "integer", "description": "Maximum messages to return (max 100)"},
                    "query": {"type": "string", "description": "Gmail search query (e.g. 'from:user@example.com')"},
                },
                "required": [],
            },
            "_fn": list_messages,
        },
        {
            "name": "gmail_get_message",
            "description": "Get the full content of a specific email message",
            "parameters": {
                "type": "object",
                "properties": {
                    "messageId": {"type": "string", "description": "The Gmail message ID"},
                },
                "required": ["messageId"],
            },
            "_fn": get_message,
        },
        {
            "name": "gmail_search_messages",
            "description": "Search Gmail messages using Gmail search syntax",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query"},
                    "maxResults": {"type": "integer", "description": "Maximum results to return"},
                },
                "required": ["query"],
            },
            "_fn": search_messages,
        },
        {
            "name": "gmail_trash_message",
            "description": "Move an email message to trash",
            "parameters": {
                "type": "object",
                "properties": {
                    "messageId": {"type": "string", "description": "The message ID to trash"},
                },
                "required": ["messageId"],
            },
            "_fn": trash_message,
        },
        {
            "name": "gmail_list_labels",
            "description": "List all Gmail labels (folders/categories)",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": list_labels,
        },
    ],
    "google-sheets": [
        {
            "name": "google_sheets_create",
            "description": "Create a new Google Spreadsheet",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Spreadsheet title"},
                    "sheetNames": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names for the sheets (tabs)",
                    },
                },
                "required": ["title"],
            },
            "_fn": create_spreadsheet,
        },
        {
            "name": "google_sheets_get",
            "description": "Get spreadsheet metadata and sheet list",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheetId": {"type": "string", "description": "The spreadsheet ID"},
                },
                "required": ["spreadsheetId"],
            },
            "_fn": get_spreadsheet,
        },
        {
            "name": "google_sheets_read_values",
            "description": "Read values from a spreadsheet range (e.g. 'Sheet1!A1:D10')",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheetId": {"type": "string", "description": "The spreadsheet ID"},
                    "range": {"type": "string", "description": "Cell range in A1 notation (e.g. 'Sheet1!A1:D10')"},
                },
                "required": ["spreadsheetId", "range"],
            },
            "_fn": read_values,
        },
        {
            "name": "google_sheets_write_values",
            "description": "Write values to a spreadsheet range",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheetId": {"type": "string", "description": "The spreadsheet ID"},
                    "range": {"type": "string", "description": "Target range in A1 notation"},
                    "values": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "2D array of values (rows of columns)",
                    },
                },
                "required": ["spreadsheetId", "range", "values"],
            },
            "_fn": write_values,
        },
        {
            "name": "google_sheets_append_values",
            "description": "Append rows to the end of a spreadsheet range",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheetId": {"type": "string", "description": "The spreadsheet ID"},
                    "range": {"type": "string", "description": "Target range (e.g. 'Sheet1')"},
                    "values": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "2D array of values to append",
                    },
                },
                "required": ["spreadsheetId", "range", "values"],
            },
            "_fn": append_values,
        },
        {
            "name": "google_sheets_clear_values",
            "description": "Clear all values from a spreadsheet range",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheetId": {"type": "string", "description": "The spreadsheet ID"},
                    "range": {"type": "string", "description": "Range to clear (e.g. 'Sheet1!A1:D10')"},
                },
                "required": ["spreadsheetId", "range"],
            },
            "_fn": clear_values,
        },
    ],
    "google-forms": [
        {
            "name": "google_forms_create",
            "description": "Create a new Google Form with optional questions",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Form title"},
                    "description": {"type": "string", "description": "Form description"},
                },
                "required": ["title"],
            },
            "_fn": create_form,
        },
        {
            "name": "google_forms_get",
            "description": "Get form details and questions",
            "parameters": {
                "type": "object",
                "properties": {
                    "formId": {"type": "string", "description": "The Google Form ID"},
                },
                "required": ["formId"],
            },
            "_fn": get_form,
        },
        {
            "name": "google_forms_list_responses",
            "description": "List all responses submitted to a form",
            "parameters": {
                "type": "object",
                "properties": {
                    "formId": {"type": "string", "description": "The Google Form ID"},
                },
                "required": ["formId"],
            },
            "_fn": list_responses,
        },
        {
            "name": "google_forms_get_response",
            "description": "Get a specific form response by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "formId": {"type": "string", "description": "The Google Form ID"},
                    "responseId": {"type": "string", "description": "The response ID"},
                },
                "required": ["formId", "responseId"],
            },
            "_fn": get_form_response,
        },
        {
            "name": "google_forms_update",
            "description": "Update a Google Form's title or description",
            "parameters": {
                "type": "object",
                "properties": {
                    "formId": {"type": "string", "description": "The Google Form ID"},
                    "title": {"type": "string", "description": "New form title"},
                    "description": {"type": "string", "description": "New form description"},
                },
                "required": ["formId"],
            },
            "_fn": update_form,
        },
    ],
}
