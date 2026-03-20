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
from app.services.slack.service import (
    slack_send_message, slack_update_message, slack_delete_message, slack_get_permalink,
    slack_list_channels, slack_get_channel_info, slack_get_channel_history,
    slack_get_thread_replies, slack_invite_to_channel, slack_create_channel, slack_archive_channel,
    slack_list_users, slack_get_user_info, slack_lookup_user_by_email, slack_set_user_status,
    slack_add_reaction, slack_remove_reaction, slack_get_reactions,
    slack_upload_file, slack_list_files, slack_delete_file,
    slack_pin_message, slack_unpin_message, slack_list_pins,
    slack_search_messages, slack_get_workspace_info, slack_get_bot_info, slack_add_reminder,
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
    "slack": [
        {
            "name": "slack_send_message",
            "description": "Send a message to a Slack channel or user. Supports text, blocks, and thread replies.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID or name (e.g. #general or C012AB3CD)"},
                "text": {"type": "string", "description": "Message text (supports Slack mrkdwn)"},
                "thread_ts": {"type": "string", "description": "Thread timestamp to reply in a thread"},
                "username": {"type": "string", "description": "Custom bot display name"},
                "icon_emoji": {"type": "string", "description": "Emoji to use as icon (e.g. :robot_face:)"},
            }, "required": ["channel", "text"]},
            "_fn": slack_send_message,
        },
        {
            "name": "slack_update_message",
            "description": "Update the content of an existing Slack message.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel containing the message"},
                "ts": {"type": "string", "description": "Timestamp of the message to update"},
                "text": {"type": "string", "description": "New message text"},
            }, "required": ["channel", "ts", "text"]},
            "_fn": slack_update_message,
        },
        {
            "name": "slack_delete_message",
            "description": "Delete a message from a Slack channel.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "ts": {"type": "string", "description": "Timestamp of the message to delete"},
            }, "required": ["channel", "ts"]},
            "_fn": slack_delete_message,
        },
        {
            "name": "slack_get_permalink",
            "description": "Get a permanent link URL to a specific Slack message.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "message_ts": {"type": "string", "description": "Timestamp of the message"},
            }, "required": ["channel", "message_ts"]},
            "_fn": slack_get_permalink,
        },
        {
            "name": "slack_list_channels",
            "description": "List all public and private channels in the Slack workspace.",
            "parameters": {"type": "object", "properties": {
                "limit": {"type": "integer", "description": "Max channels to return (default 100)"},
                "types": {"type": "string", "description": "Channel types: public_channel, private_channel, mpim, im"},
                "exclude_archived": {"type": "boolean", "description": "Exclude archived channels"},
            }, "required": []},
            "_fn": slack_list_channels,
        },
        {
            "name": "slack_get_channel_info",
            "description": "Get detailed information about a specific Slack channel.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
            }, "required": ["channel"]},
            "_fn": slack_get_channel_info,
        },
        {
            "name": "slack_get_channel_history",
            "description": "Retrieve recent messages from a Slack channel.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "limit": {"type": "integer", "description": "Number of messages to return"},
                "oldest": {"type": "string", "description": "Start of time range (Unix timestamp)"},
                "latest": {"type": "string", "description": "End of time range (Unix timestamp)"},
            }, "required": ["channel"]},
            "_fn": slack_get_channel_history,
        },
        {
            "name": "slack_get_thread_replies",
            "description": "Get all replies in a message thread.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "ts": {"type": "string", "description": "Timestamp of the parent message"},
                "limit": {"type": "integer", "description": "Max replies to return"},
            }, "required": ["channel", "ts"]},
            "_fn": slack_get_thread_replies,
        },
        {
            "name": "slack_create_channel",
            "description": "Create a new Slack channel.",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string", "description": "Channel name (lowercase, no spaces)"},
                "is_private": {"type": "boolean", "description": "Whether the channel should be private"},
            }, "required": ["name"]},
            "_fn": slack_create_channel,
        },
        {
            "name": "slack_invite_to_channel",
            "description": "Invite one or more users to a Slack channel.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "users": {"type": "string", "description": "Comma-separated user IDs to invite"},
            }, "required": ["channel", "users"]},
            "_fn": slack_invite_to_channel,
        },
        {
            "name": "slack_archive_channel",
            "description": "Archive a Slack channel.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID to archive"},
            }, "required": ["channel"]},
            "_fn": slack_archive_channel,
        },
        {
            "name": "slack_list_users",
            "description": "List all members of the Slack workspace.",
            "parameters": {"type": "object", "properties": {
                "limit": {"type": "integer", "description": "Max users to return"},
            }, "required": []},
            "_fn": slack_list_users,
        },
        {
            "name": "slack_get_user_info",
            "description": "Get profile information about a specific Slack user.",
            "parameters": {"type": "object", "properties": {
                "user": {"type": "string", "description": "User ID (e.g. U012AB3CD)"},
            }, "required": ["user"]},
            "_fn": slack_get_user_info,
        },
        {
            "name": "slack_lookup_user_by_email",
            "description": "Find a Slack user by their email address.",
            "parameters": {"type": "object", "properties": {
                "email": {"type": "string", "description": "Email address to look up"},
            }, "required": ["email"]},
            "_fn": slack_lookup_user_by_email,
        },
        {
            "name": "slack_add_reaction",
            "description": "Add an emoji reaction to a Slack message.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "timestamp": {"type": "string", "description": "Message timestamp"},
                "name": {"type": "string", "description": "Emoji name without colons (e.g. thumbsup)"},
            }, "required": ["channel", "timestamp", "name"]},
            "_fn": slack_add_reaction,
        },
        {
            "name": "slack_remove_reaction",
            "description": "Remove an emoji reaction from a Slack message.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "timestamp": {"type": "string", "description": "Message timestamp"},
                "name": {"type": "string", "description": "Emoji name to remove"},
            }, "required": ["channel", "timestamp", "name"]},
            "_fn": slack_remove_reaction,
        },
        {
            "name": "slack_get_reactions",
            "description": "Get all emoji reactions on a Slack message.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "timestamp": {"type": "string", "description": "Message timestamp"},
            }, "required": ["channel", "timestamp"]},
            "_fn": slack_get_reactions,
        },
        {
            "name": "slack_upload_file",
            "description": "Upload a text file or snippet to Slack.",
            "parameters": {"type": "object", "properties": {
                "content": {"type": "string", "description": "Text content of the file"},
                "filename": {"type": "string", "description": "Filename (e.g. report.txt)"},
                "title": {"type": "string", "description": "Display title of the file"},
                "channels": {"type": "string", "description": "Comma-separated channel IDs to share the file in"},
                "initial_comment": {"type": "string", "description": "Message to accompany the file"},
            }, "required": ["content"]},
            "_fn": slack_upload_file,
        },
        {
            "name": "slack_list_files",
            "description": "List files shared in the Slack workspace.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Filter files by channel"},
                "count": {"type": "integer", "description": "Number of files to return"},
                "types": {"type": "string", "description": "File types: all, spaces, snippets, images, gdocs, zips, pdfs"},
            }, "required": []},
            "_fn": slack_list_files,
        },
        {
            "name": "slack_delete_file",
            "description": "Delete a file from Slack.",
            "parameters": {"type": "object", "properties": {
                "file": {"type": "string", "description": "File ID to delete"},
            }, "required": ["file"]},
            "_fn": slack_delete_file,
        },
        {
            "name": "slack_pin_message",
            "description": "Pin a message to a Slack channel.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "timestamp": {"type": "string", "description": "Message timestamp to pin"},
            }, "required": ["channel", "timestamp"]},
            "_fn": slack_pin_message,
        },
        {
            "name": "slack_unpin_message",
            "description": "Unpin a message from a Slack channel.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "timestamp": {"type": "string", "description": "Message timestamp to unpin"},
            }, "required": ["channel", "timestamp"]},
            "_fn": slack_unpin_message,
        },
        {
            "name": "slack_list_pins",
            "description": "List all pinned items in a Slack channel.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
            }, "required": ["channel"]},
            "_fn": slack_list_pins,
        },
        {
            "name": "slack_search_messages",
            "description": "Search for messages in Slack matching a query.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Search query string"},
                "count": {"type": "integer", "description": "Number of results to return"},
                "sort": {"type": "string", "description": "Sort by: score or timestamp"},
            }, "required": ["query"]},
            "_fn": slack_search_messages,
        },
        {
            "name": "slack_get_workspace_info",
            "description": "Get information about the Slack workspace (team name, domain, etc).",
            "parameters": {"type": "object", "properties": {}, "required": []},
            "_fn": slack_get_workspace_info,
        },
        {
            "name": "slack_get_bot_info",
            "description": "Get information about the authenticated Slack bot (auth.test).",
            "parameters": {"type": "object", "properties": {}, "required": []},
            "_fn": slack_get_bot_info,
        },
        {
            "name": "slack_add_reminder",
            "description": "Create a reminder for a user in Slack.",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string", "description": "Reminder message"},
                "time": {"type": "string", "description": "When to send: Unix timestamp or natural language like 'in 30 minutes'"},
                "user": {"type": "string", "description": "User ID to remind (defaults to bot user)"},
            }, "required": ["text", "time"]},
            "_fn": slack_add_reminder,
        },
    ],
}
