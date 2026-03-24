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
from app.services.ml.router import (
    ml_upload_dataset, ml_train_model, ml_predict,
    ml_get_model_info, ml_list_models, ml_list_datasets,
    ml_analyze_dataset, ml_preview_dataset,
    ml_train_supervised, ml_train_unsupervised,
    ml_list_algorithms,
)
from app.services.context.router import (
    context_upload_document, context_query, context_list_documents,
    context_delete_document, context_clear_collection, context_list_collections,
)
from app.services.cv_router.router import (
    cv_train_model, cv_load_model, cv_infer, cv_list_models,
)
from app.services.twilio.router import (
    make_call, send_sms, get_call_status, get_message_status,
)
from app.services.elevenlabs.router import (
    text_to_speech, list_voices, get_voice,
)
from app.services.postgresql.router import (
    execute_query, select_rows, insert_row, update_rows, delete_rows,
)
from app.services.call_conversation.router import (
    start_conversation_call as _start_conversation_call_fn,
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
from app.services.telegram.service import (
    telegram_get_me, telegram_get_my_commands, telegram_set_my_commands,
    telegram_send_message, telegram_edit_message, telegram_delete_message,
    telegram_forward_message, telegram_copy_message, telegram_pin_message,
    telegram_unpin_message, telegram_unpin_all_messages,
    telegram_send_photo, telegram_send_document, telegram_send_audio,
    telegram_send_video, telegram_send_animation, telegram_send_sticker,
    telegram_send_location, telegram_send_poll,
    telegram_get_chat, telegram_get_chat_member_count, telegram_get_chat_member,
    telegram_ban_chat_member, telegram_unban_chat_member, telegram_restrict_chat_member,
    telegram_promote_chat_member, telegram_set_chat_title, telegram_set_chat_description,
    telegram_leave_chat, telegram_export_invite_link,
    telegram_get_file, telegram_answer_callback_query,
    telegram_set_webhook, telegram_delete_webhook, telegram_get_webhook_info,
)
from app.services.aws.s3_service import (
    s3_upload_text, s3_download_as_text, s3_delete_object, s3_copy_object,
    s3_move_object, s3_get_object_metadata,
    s3_list_objects, s3_list_buckets,
    s3_generate_presigned_url, s3_generate_presigned_post,
    s3_create_bucket, s3_delete_bucket, s3_get_bucket_location,
    s3_get_object_acl, s3_put_object_acl,
    s3_get_bucket_versioning, s3_put_bucket_versioning, s3_list_object_versions,
    s3_get_object_tags, s3_put_object_tags, s3_delete_object_tags,
    s3_put_bucket_website, s3_get_bucket_website, s3_delete_bucket_website,
)

ServiceFn = Callable[[str, dict[str, Any]], Awaitable[dict]]


# ─────────────────────────────────────────────
# Wrapper functions for secret-based services (Twilio, ElevenLabs, PostgreSQL)
# These fetch credentials from UserSecret table and call the underlying functions
# ─────────────────────────────────────────────

async def _twilio_make_call_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for make_call that fetches Twilio credentials."""
    from app.services.twilio.router import _get_twilio_credentials
    from uuid import UUID
    account_sid, auth_token = await _get_twilio_credentials(db, UUID(user_id))
    return await make_call(account_sid, auth_token, params)


async def _twilio_send_sms_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for send_sms that fetches Twilio credentials."""
    from app.services.twilio.router import _get_twilio_credentials
    from uuid import UUID
    account_sid, auth_token = await _get_twilio_credentials(db, UUID(user_id))
    return await send_sms(account_sid, auth_token, params)


async def _twilio_get_call_status_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for get_call_status that fetches Twilio credentials."""
    from app.services.twilio.router import _get_twilio_credentials
    from uuid import UUID
    account_sid, auth_token = await _get_twilio_credentials(db, UUID(user_id))
    return await get_call_status(account_sid, auth_token, params)


async def _twilio_get_message_status_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for get_message_status that fetches Twilio credentials."""
    from app.services.twilio.router import _get_twilio_credentials
    from uuid import UUID
    account_sid, auth_token = await _get_twilio_credentials(db, UUID(user_id))
    return await get_message_status(account_sid, auth_token, params)


async def _twilio_conversation_call_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for start_conversation_call that is called by the agent."""
    return await _start_conversation_call_fn(user_id, params, db)


async def _elevenlabs_tts_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for text_to_speech that fetches ElevenLabs API key."""
    from app.services.elevenlabs.router import _get_elevenlabs_api_key
    from uuid import UUID
    api_key = await _get_elevenlabs_api_key(db, UUID(user_id))
    return await text_to_speech(api_key, params)


async def _elevenlabs_list_voices_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for list_voices that fetches ElevenLabs API key."""
    from app.services.elevenlabs.router import _get_elevenlabs_api_key
    from uuid import UUID
    api_key = await _get_elevenlabs_api_key(db, UUID(user_id))
    return await list_voices(api_key, params)


async def _elevenlabs_get_voice_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for get_voice that fetches ElevenLabs API key."""
    from app.services.elevenlabs.router import _get_elevenlabs_api_key
    from uuid import UUID
    api_key = await _get_elevenlabs_api_key(db, UUID(user_id))
    return await get_voice(api_key, params)


async def _postgres_query_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for execute_query that fetches PostgreSQL connection string."""
    from app.services.postgresql.router import _get_connection_string
    from uuid import UUID
    conn_str = await _get_connection_string(db, UUID(user_id))
    return await execute_query(conn_str, params)


async def _postgres_select_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for select_rows that fetches PostgreSQL connection string."""
    from app.services.postgresql.router import _get_connection_string
    from uuid import UUID
    conn_str = await _get_connection_string(db, UUID(user_id))
    return await select_rows(conn_str, params)


async def _postgres_insert_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for insert_row that fetches PostgreSQL connection string."""
    from app.services.postgresql.router import _get_connection_string
    from uuid import UUID
    conn_str = await _get_connection_string(db, UUID(user_id))
    return await insert_row(conn_str, params)


async def _postgres_update_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for update_rows that fetches PostgreSQL connection string."""
    from app.services.postgresql.router import _get_connection_string
    from uuid import UUID
    conn_str = await _get_connection_string(db, UUID(user_id))
    return await update_rows(conn_str, params)


async def _postgres_delete_wrapper(user_id: str, params: dict[str, Any], db) -> dict:
    """Wrapper for delete_rows that fetches PostgreSQL connection string."""
    from app.services.postgresql.router import _get_connection_string
    from uuid import UUID
    conn_str = await _get_connection_string(db, UUID(user_id))
    return await delete_rows(conn_str, params)

# Tools that don't require OAuth credentials (use user_id instead)
CREDENTIAL_LESS_TOOLS = {
    "ml-trainer",  # Legacy
    "data-prep",
    "supervised-train",
    "unsupervised-train",
    "model-inference",
    "context-store",
    "cv-train",
    "cv-inference",
    "twilio",
    "elevenlabs",
    "postgresql",
}


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
    "ml-trainer": [
        {
            "name": "ml_upload_dataset",
            "description": "Upload a CSV or JSON dataset for ML training",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_content": {"type": "string", "description": "Base64-encoded file content"},
                    "filename": {"type": "string", "description": "Original filename"},
                    "file_type": {"type": "string", "enum": ["csv", "json"], "description": "File format"},
                },
                "required": ["file_content", "filename", "file_type"],
            },
            "_fn": ml_upload_dataset,
        },
        {
            "name": "ml_train_model",
            "description": "Train a machine learning model on a dataset",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "ID of the dataset to train on"},
                    "algorithm": {
                        "type": "string",
                        "enum": [
                            "logistic_regression", "random_forest_classifier", "svm_classifier",
                            "gradient_boosting_classifier", "adaboost_classifier", "catboost_classifier",
                            "linear_regression", "random_forest_regressor", "svm_regressor",
                            "gradient_boosting_regressor", "adaboost_regressor", "catboost_regressor",
                            "kmeans", "dbscan", "pca"
                        ],
                        "description": "ML algorithm to use",
                    },
                    "model_type": {
                        "type": "string",
                        "enum": ["classification", "regression", "clustering", "dimensionality_reduction"],
                        "description": "Type of ML task",
                    },
                    "target_column": {"type": "string", "description": "Target column for supervised learning"},
                    "feature_columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Feature columns to use (optional, uses all if not specified)",
                    },
                    "name": {"type": "string", "description": "Optional name for the model"},
                },
                "required": ["dataset_id", "algorithm", "model_type"],
            },
            "_fn": ml_train_model,
        },
        {
            "name": "ml_predict",
            "description": "Run predictions using a trained model",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "string", "description": "ID of the trained model"},
                    "input_data": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Input data as array of objects",
                    },
                },
                "required": ["model_id", "input_data"],
            },
            "_fn": ml_predict,
        },
        {
            "name": "ml_get_model_info",
            "description": "Get information and metrics about a trained model",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "string", "description": "ID of the model"},
                },
                "required": ["model_id"],
            },
            "_fn": ml_get_model_info,
        },
        {
            "name": "ml_list_models",
            "description": "List all trained models",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": ml_list_models,
        },
        {
            "name": "ml_list_datasets",
            "description": "List all uploaded datasets. Returns dataset IDs, names, and column info. ALWAYS call this first to find the correct dataset_id (UUID) before training - never use the filename as dataset_id.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": ml_list_datasets,
        },
    ],
    # New ML node types
    "data-prep": [
        {
            "name": "ml_upload_dataset",
            "description": "Upload a CSV or JSON dataset for ML training",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_content": {"type": "string", "description": "Base64-encoded file content"},
                    "filename": {"type": "string", "description": "Original filename"},
                    "file_type": {"type": "string", "enum": ["csv", "json"], "description": "File format"},
                },
                "required": ["file_content", "filename", "file_type"],
            },
            "_fn": ml_upload_dataset,
        },
        {
            "name": "ml_analyze_dataset",
            "description": "Analyze a dataset to understand its structure. Returns: (1) all_column_names - exact column names (case-sensitive), (2) sample_rows - first 5 rows of actual data, (3) column_dtypes - data types, (4) statistics per column. ALWAYS call this before training to see the data and use correct column names!",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "UUID of the dataset (get from ml_list_datasets)"},
                },
                "required": ["dataset_id"],
            },
            "_fn": ml_analyze_dataset,
        },
        {
            "name": "ml_preview_dataset",
            "description": "Preview first N rows of a dataset. Shows actual data values and exact column names (case-sensitive).",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "UUID of the dataset (get from ml_list_datasets)"},
                    "n_rows": {"type": "integer", "description": "Number of rows to preview (default 10)"},
                },
                "required": ["dataset_id"],
            },
            "_fn": ml_preview_dataset,
        },
        {
            "name": "ml_list_datasets",
            "description": "List all uploaded datasets. Returns dataset IDs (UUIDs), filenames, row counts, and column names. ALWAYS call this first to find the correct dataset_id before any other dataset operation.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": ml_list_datasets,
        },
    ],
    "supervised-train": [
        {
            "name": "ml_list_algorithms",
            "description": "List all available ML algorithms with their hyperparameters (iterations, learning_rate, n_estimators, max_depth, etc.). Call this to see what parameters each algorithm accepts.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": ml_list_algorithms,
        },
        {
            "name": "ml_train_supervised",
            "description": "Train a supervised ML model. IMPORTANT: (1) Call ml_list_datasets to get dataset UUID. (2) Call ml_analyze_dataset to see exact column names (case-sensitive). (3) Optionally call ml_list_algorithms to see hyperparameter options. Key hyperparams: iterations/max_iter (epochs), learning_rate, n_estimators, max_depth.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "UUID of the dataset (from ml_list_datasets, NOT the filename)"},
                    "algorithm": {
                        "type": "string",
                        "enum": [
                            "logistic_regression", "random_forest_classifier", "svm_classifier",
                            "gradient_boosting_classifier", "adaboost_classifier", "catboost_classifier",
                            "linear_regression", "random_forest_regressor", "svm_regressor",
                            "gradient_boosting_regressor", "adaboost_regressor", "catboost_regressor"
                        ],
                        "description": "ML algorithm to use",
                    },
                    "target_column": {"type": "string", "description": "Target column name EXACTLY as shown in the dataset (case-sensitive)"},
                    "feature_columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Feature columns to use (optional, uses all numeric columns if not specified)",
                    },
                    "model_name": {"type": "string", "description": "Optional name for the model"},
                    "preprocessing": {
                        "type": "object",
                        "description": "Preprocessing configuration",
                        "properties": {
                            "normalization": {
                                "type": "string",
                                "enum": ["standard", "minmax", "robust", "none"],
                                "description": "Normalization method (default: standard)",
                            },
                            "handle_missing": {
                                "type": "string",
                                "enum": ["drop", "mean", "median", "mode", "zero"],
                                "description": "How to handle missing values (default: zero)",
                            },
                            "train_size": {"type": "number", "description": "Training set proportion (default: 0.7)"},
                            "val_size": {"type": "number", "description": "Validation set proportion (default: 0.15)"},
                            "test_size": {"type": "number", "description": "Test set proportion (default: 0.15)"},
                        },
                    },
                    "hyperparameters": {
                        "type": "object",
                        "description": "Algorithm-specific params. Examples: catboost={iterations:200, learning_rate:0.05, depth:6}, random_forest={n_estimators:200, max_depth:15}, logistic={max_iter:2000, C:0.5}, gradient_boost={n_estimators:150, learning_rate:0.1, max_depth:5}",
                    },
                },
                "required": ["dataset_id", "algorithm", "target_column"],
            },
            "_fn": ml_train_supervised,
        },
        {
            "name": "ml_list_models",
            "description": "List all trained models with IDs, algorithms, metrics, and feature_names.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": ml_list_models,
        },
        {
            "name": "ml_get_model_info",
            "description": "Get detailed info about a trained model including metrics and hyperparameters used.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "string", "description": "UUID of the model"},
                },
                "required": ["model_id"],
            },
            "_fn": ml_get_model_info,
        },
    ],
    "unsupervised-train": [
        {
            "name": "ml_list_algorithms",
            "description": "List all available ML algorithms with their hyperparameters. Call to see clustering options like kmeans (n_clusters, max_iter) or dbscan (eps, min_samples).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": ml_list_algorithms,
        },
        {
            "name": "ml_train_unsupervised",
            "description": "Train an unsupervised ML model. IMPORTANT: (1) First call ml_list_datasets to get the dataset UUID. (2) For kmeans, specify n_clusters in hyperparameters. Algorithms: kmeans (clustering), dbscan (density clustering), pca (dimensionality reduction).",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "UUID of the dataset (from ml_list_datasets, NOT the filename)"},
                    "algorithm": {
                        "type": "string",
                        "enum": ["kmeans", "dbscan", "pca"],
                        "description": "ML algorithm: kmeans (clustering), dbscan (density clustering), pca (dimensionality reduction)",
                    },
                    "feature_columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Feature columns to use (optional, uses all numeric columns if not specified)",
                    },
                    "model_name": {"type": "string", "description": "Optional name for the model"},
                    "preprocessing": {
                        "type": "object",
                        "description": "Preprocessing configuration",
                        "properties": {
                            "normalization": {
                                "type": "string",
                                "enum": ["standard", "minmax", "robust", "none"],
                                "description": "Normalization method (default: standard)",
                            },
                            "handle_missing": {
                                "type": "string",
                                "enum": ["drop", "mean", "median", "mode", "zero"],
                                "description": "How to handle missing values (default: zero)",
                            },
                        },
                    },
                    "hyperparameters": {
                        "type": "object",
                        "description": "Algorithm params: kmeans needs {n_clusters: 3}, dbscan needs {eps: 0.5, min_samples: 5}, pca needs {n_components: 2}",
                    },
                },
                "required": ["dataset_id", "algorithm"],
            },
            "_fn": ml_train_unsupervised,
        },
        {
            "name": "ml_list_models",
            "description": "List all trained models with their IDs, algorithms, and metrics.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": ml_list_models,
        },
        {
            "name": "ml_get_model_info",
            "description": "Get detailed info about a specific model including metrics and feature_names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "string", "description": "UUID of the model"},
                },
                "required": ["model_id"],
            },
            "_fn": ml_get_model_info,
        },
    ],
    "model-inference": [
        {
            "name": "ml_predict",
            "description": "Run predictions using a trained model. IMPORTANT: (1) First call ml_list_models to get available model IDs and their feature_names. (2) Provide input_data as array of objects where each object has keys matching the model's feature_names exactly. Returns predictions (class labels or values) and probabilities for classifiers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "string", "description": "UUID of the trained model (from ml_list_models)"},
                    "input_data": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Array of test cases. Each object should have keys matching the model's feature_names (case-sensitive). Example: [{'Glucose': 120, 'BMI': 25.5, ...}]",
                    },
                },
                "required": ["model_id", "input_data"],
            },
            "_fn": ml_predict,
        },
        {
            "name": "ml_list_models",
            "description": "List all trained models. Returns model IDs, names, algorithms, metrics, and feature_names needed for predictions. ALWAYS call this first to see available models and their required features.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": ml_list_models,
        },
        {
            "name": "ml_get_model_info",
            "description": "Get detailed info about a specific model including metrics (accuracy, f1_score, etc.) and feature_names required for predictions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "string", "description": "UUID of the model"},
                },
                "required": ["model_id"],
            },
            "_fn": ml_get_model_info,
        },
    ],
    "context-store": [
        {
            "name": "context_upload_document",
            "description": "Upload a PDF or text document to the vector store for semantic search",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {"type": "string", "description": "Name of the collection to add to"},
                    "file_content": {"type": "string", "description": "Base64-encoded file content"},
                    "filename": {"type": "string", "description": "Original filename"},
                    "file_type": {"type": "string", "enum": ["pdf", "txt", "md"], "description": "File format"},
                    "chunk_size": {"type": "integer", "description": "Characters per chunk (default 500)"},
                    "chunk_overlap": {"type": "integer", "description": "Overlap between chunks (default 50)"},
                },
                "required": ["collection_name", "file_content", "filename", "file_type"],
            },
            "_fn": context_upload_document,
        },
        {
            "name": "context_query",
            "description": "Search the vector store for relevant context using semantic similarity",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {"type": "string", "description": "Name of the collection to search"},
                    "query_text": {"type": "string", "description": "Search query"},
                    "top_k": {"type": "integer", "description": "Number of results to return (default 5)"},
                },
                "required": ["collection_name", "query_text"],
            },
            "_fn": context_query,
        },
        {
            "name": "context_list_documents",
            "description": "List all documents in a vector store collection",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {"type": "string", "description": "Name of the collection"},
                },
                "required": ["collection_name"],
            },
            "_fn": context_list_documents,
        },
        {
            "name": "context_delete_document",
            "description": "Remove a document from the vector store",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {"type": "string", "description": "Name of the collection"},
                    "document_id": {"type": "string", "description": "ID of the document to delete"},
                },
                "required": ["collection_name", "document_id"],
            },
            "_fn": context_delete_document,
        },
        {
            "name": "context_clear_collection",
            "description": "Clear all documents from a vector store collection",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection_name": {"type": "string", "description": "Name of the collection to clear"},
                },
                "required": ["collection_name"],
            },
            "_fn": context_clear_collection,
        },
        {
            "name": "context_list_collections",
            "description": "List all vector store collections",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": context_list_collections,
        },
    ],
    "cv-train": [
        {
            "name": "cv_train_model",
            "description": "Train a computer vision model. Supports classification (ResNet, EfficientNet, VGG, MobileNet, DenseNet, ViT, ConvNeXt), detection (Faster R-CNN, SSD, RetinaNet, YOLOv5, YOLOv8), and segmentation (U-Net, DeepLabV3, FCN, PSPNet, Mask R-CNN). IMPORTANT: Provide absolute path to dataset folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "enum": ["classification", "detection", "segmentation"],
                        "description": "CV task type",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model architecture (e.g., resnet, yolov8, unet)",
                    },
                    "dataset_path": {
                        "type": "string",
                        "description": "Absolute path to the dataset folder",
                    },
                    "epochs": {
                        "type": "integer",
                        "description": "Number of training epochs (default: 10)",
                    },
                    "optimizer": {
                        "type": "string",
                        "enum": ["adam", "sgd", "adamw", "rmsprop"],
                        "description": "Optimizer to use (default: adam)",
                    },
                    "learning_rate": {
                        "type": "number",
                        "description": "Learning rate (default: 0.001)",
                    },
                    "batch_size": {
                        "type": "integer",
                        "description": "Batch size (default: 32)",
                    },
                    "image_size": {
                        "type": "integer",
                        "description": "Input image size (default: 224)",
                    },
                    "train_pct": {
                        "type": "number",
                        "description": "Training set percentage (default: 0.7)",
                    },
                    "val_pct": {
                        "type": "number",
                        "description": "Validation set percentage (default: 0.15)",
                    },
                    "test_pct": {
                        "type": "number",
                        "description": "Test set percentage (default: 0.15)",
                    },
                    "save_local": {
                        "type": "boolean",
                        "description": "Save model locally (default: true)",
                    },
                    "upload_to_s3": {
                        "type": "boolean",
                        "description": "Upload model to S3 (default: false)",
                    },
                    "s3_model_path": {
                        "type": "string",
                        "description": "S3 path for model upload",
                    },
                    "custom_model_name": {
                        "type": "string",
                        "description": "Custom name for the saved model",
                    },
                },
                "required": ["task", "model", "dataset_path"],
            },
            "_fn": cv_train_model,
        },
        {
            "name": "cv_list_models",
            "description": "List all saved CV models available for inference",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": cv_list_models,
        },
    ],
    "cv-inference": [
        {
            "name": "cv_load_model",
            "description": "Load a CV model for inference. Can load from local path, saved models, or S3. IMPORTANT: Call this before running inference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "enum": ["classification", "detection", "segmentation"],
                        "description": "CV task type",
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Model architecture (e.g., resnet, yolov8, unet)",
                    },
                    "model_path": {
                        "type": "string",
                        "description": "Local path to model weights (.pt file)",
                    },
                    "model_source": {
                        "type": "string",
                        "enum": ["local", "s3", "trained"],
                        "description": "Where to load the model from",
                    },
                    "s3_model_path": {
                        "type": "string",
                        "description": "S3 path if loading from S3",
                    },
                    "dataset_path": {
                        "type": "string",
                        "description": "Path to dataset for class names (optional)",
                    },
                    "num_classes": {
                        "type": "integer",
                        "description": "Number of classes (required for segmentation)",
                    },
                },
                "required": ["task_type", "model_name"],
            },
            "_fn": cv_load_model,
        },
        {
            "name": "cv_infer",
            "description": "Run CV inference on an image. Supports local file paths, image URLs, and webcam. Returns predictions (class labels, bounding boxes, or segmentation masks) AND an annotated image showing the detected objects/segments visually overlaid on the original image. The annotated_image is returned as a base64-encoded data URL that can be displayed directly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "input_type": {
                        "type": "string",
                        "enum": ["file", "url", "webcam"],
                        "description": "Type of image input",
                    },
                    "image_path": {
                        "type": "string",
                        "description": "Local path to image file (for input_type=file)",
                    },
                    "image_url": {
                        "type": "string",
                        "description": "URL of image (for input_type=url)",
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "description": "Confidence threshold for predictions (default: 0.5)",
                    },
                },
                "required": ["input_type"],
            },
            "_fn": cv_infer,
        },
        {
            "name": "cv_list_models",
            "description": "List all saved CV models with their paths and metadata",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": cv_list_models,
        },
    ],
    "twilio": [
        {
            "name": "twilio_make_call",
            "description": "Make an outbound phone call using Twilio with TwiML or webhook URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient phone number in E.164 format (+1234567890)"},
                    "from": {"type": "string", "description": "Your Twilio phone number"},
                    "twiml": {"type": "string", "description": "TwiML XML or URL to TwiML endpoint"},
                    "statusCallback": {"type": "string", "description": "Optional webhook URL for call status updates"},
                },
                "required": ["to", "from", "twiml"],
            },
            "_fn": _twilio_make_call_wrapper,
        },
        {
            "name": "twilio_send_sms",
            "description": "Send an SMS message using Twilio",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient phone number in E.164 format"},
                    "from": {"type": "string", "description": "Your Twilio phone number"},
                    "body": {"type": "string", "description": "SMS message body (max 1600 chars)"},
                },
                "required": ["to", "from", "body"],
            },
            "_fn": _twilio_send_sms_wrapper,
        },
        {
            "name": "twilio_get_call_status",
            "description": "Get the status of a call by SID",
            "parameters": {
                "type": "object",
                "properties": {
                    "sid": {"type": "string", "description": "Call SID (starts with CA)"},
                },
                "required": ["sid"],
            },
            "_fn": _twilio_get_call_status_wrapper,
        },
        {
            "name": "twilio_get_message_status",
            "description": "Get the status of an SMS message by SID",
            "parameters": {
                "type": "object",
                "properties": {
                    "sid": {"type": "string", "description": "Message SID (starts with SM)"},
                },
                "required": ["sid"],
            },
            "_fn": _twilio_get_message_status_wrapper,
        },
        {
            "name": "twilio_make_conversation_call",
            "description": "Make an outbound phone call with real-time AI voice conversation. The AI agent will have a back-and-forth voice conversation with the person who answers. Uses ElevenLabs Conversational AI for natural speech. The call continues until the user or agent ends it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient phone number in E.164 format (+1234567890)"},
                    "from": {"type": "string", "description": "Your Twilio phone number in E.164 format"},
                    "system_prompt": {"type": "string", "description": "Instructions for the AI voice agent describing its role, personality, and what to discuss during the call"},
                    "first_message": {"type": "string", "description": "The first thing the AI says when the call is answered (greeting)"},
                    "voice_id": {"type": "string", "description": "Optional ElevenLabs voice ID for the AI voice"},
                },
                "required": ["to", "from", "system_prompt", "first_message"],
            },
            "_fn": _twilio_conversation_call_wrapper,
        },
    ],
    "elevenlabs": [
        {
            "name": "elevenlabs_text_to_speech",
            "description": "Convert text to natural-sounding speech using ElevenLabs. Returns base64-encoded audio that can be played or saved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to convert to speech (max 5000 chars)"},
                    "voice_id": {"type": "string", "description": "Voice ID (use elevenlabs_list_voices to get available voices)"},
                    "model_id": {"type": "string", "description": "Model ID (default: eleven_v3)"},
                    "stability": {"type": "number", "description": "Voice stability 0.0-1.0 (default: 0.5)"},
                    "similarity_boost": {"type": "number", "description": "Similarity boost 0.0-1.0 (default: 0.5)"},
                },
                "required": ["text", "voice_id"],
            },
            "_fn": _elevenlabs_tts_wrapper,
        },
        {
            "name": "elevenlabs_list_voices",
            "description": "List all available ElevenLabs voices with their IDs and names",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": _elevenlabs_list_voices_wrapper,
        },
        {
            "name": "elevenlabs_get_voice",
            "description": "Get details of a specific voice by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "voice_id": {"type": "string", "description": "Voice ID"},
                },
                "required": ["voice_id"],
            },
            "_fn": _elevenlabs_get_voice_wrapper,
        },
        {
            "name": "twilio_make_conversation_call",
            "description": "Make an outbound phone call with real-time AI voice conversation. The AI agent will have a back-and-forth voice conversation with the person who answers. Uses ElevenLabs Conversational AI for natural speech. The call continues until the user or agent ends it. Requires both Twilio and ElevenLabs credentials configured.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient phone number in E.164 format (+1234567890)"},
                    "from": {"type": "string", "description": "Your Twilio phone number in E.164 format"},
                    "system_prompt": {"type": "string", "description": "Instructions for the AI voice agent describing its role, personality, and what to discuss during the call"},
                    "first_message": {"type": "string", "description": "The first thing the AI says when the call is answered (greeting)"},
                    "voice_id": {"type": "string", "description": "Optional ElevenLabs voice ID for the AI voice"},
                },
                "required": ["to", "from", "system_prompt", "first_message"],
            },
            "_fn": _twilio_conversation_call_wrapper,
        },
    ],
    "postgresql": [
        {
            "name": "postgres_query",
            "description": "Execute a raw SQL query (SELECT, INSERT, UPDATE, DELETE) on PostgreSQL database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query to execute"},
                    "params": {"type": "array", "items": {"type": "string"}, "description": "Query parameters for placeholders ($1, $2, etc)"},
                },
                "required": ["query"],
            },
            "_fn": _postgres_query_wrapper,
        },
        {
            "name": "postgres_select",
            "description": "Select rows from a PostgreSQL table with optional WHERE clause and LIMIT",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name"},
                    "columns": {"type": "string", "description": "Columns to select (comma-separated or * for all)"},
                    "where": {"type": "string", "description": "Optional WHERE clause (without the WHERE keyword)"},
                    "limit": {"type": "integer", "description": "Optional max number of rows to return"},
                },
                "required": ["table"],
            },
            "_fn": _postgres_select_wrapper,
        },
        {
            "name": "postgres_insert",
            "description": "Insert a new row into a PostgreSQL table",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name"},
                    "data": {"type": "object", "description": "Row data as object with column names as keys"},
                },
                "required": ["table", "data"],
            },
            "_fn": _postgres_insert_wrapper,
        },
        {
            "name": "postgres_update",
            "description": "Update rows in a PostgreSQL table matching WHERE clause",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name"},
                    "data": {"type": "object", "description": "Data to update as object with column names as keys"},
                    "where": {"type": "string", "description": "WHERE clause (required for safety)"},
                },
                "required": ["table", "data", "where"],
            },
            "_fn": _postgres_update_wrapper,
        },
        {
            "name": "postgres_delete",
            "description": "Delete rows from a PostgreSQL table matching WHERE clause",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name"},
                    "where": {"type": "string", "description": "WHERE clause (required for safety)"},
                },
                "required": ["table", "where"],
            },
            "_fn": _postgres_delete_wrapper,
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
            "name": "slack_get_channel_history",
            "description": "Retrieve recent messages from a Slack channel.",
            "parameters": {"type": "object", "properties": {
                "channel": {"type": "string", "description": "Channel ID"},
                "limit": {"type": "integer", "description": "Number of messages to return"},
            }, "required": ["channel"]},
            "_fn": slack_get_channel_history,
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
            "name": "slack_upload_file",
            "description": "Upload a text file or snippet to Slack.",
            "parameters": {"type": "object", "properties": {
                "content": {"type": "string", "description": "Text content of the file"},
                "filename": {"type": "string", "description": "Filename (e.g. report.txt)"},
                "channels": {"type": "string", "description": "Comma-separated channel IDs to share the file in"},
            }, "required": ["content"]},
            "_fn": slack_upload_file,
        },
        {
            "name": "slack_search_messages",
            "description": "Search for messages in Slack matching a query.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string", "description": "Search query string"},
                "count": {"type": "integer", "description": "Number of results to return"},
            }, "required": ["query"]},
            "_fn": slack_search_messages,
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
    "telegram": [
        {
            "name": "telegram_send_message",
            "description": "Send a text message to a Telegram chat, group, or channel. Supports HTML formatting.",
            "parameters": {"type": "object", "properties": {
                "chat_id": {"type": "string", "description": "Target chat ID or @username"},
                "text": {"type": "string", "description": "Message text (HTML supported)"},
                "parse_mode": {"type": "string", "description": "Formatting: HTML or Markdown"},
                "disable_notification": {"type": "boolean", "description": "Send silently"},
            }, "required": ["chat_id", "text"]},
            "_fn": telegram_send_message,
        },
        {
            "name": "telegram_edit_message",
            "description": "Edit the text of an existing Telegram message.",
            "parameters": {"type": "object", "properties": {
                "chat_id": {"type": "string", "description": "Chat ID"},
                "message_id": {"type": "integer", "description": "Message ID to edit"},
                "text": {"type": "string", "description": "New message text"},
            }, "required": ["chat_id", "message_id", "text"]},
            "_fn": telegram_edit_message,
        },
        {
            "name": "telegram_delete_message",
            "description": "Delete a message from a Telegram chat.",
            "parameters": {"type": "object", "properties": {
                "chat_id": {"type": "string", "description": "Chat ID"},
                "message_id": {"type": "integer", "description": "Message ID to delete"},
            }, "required": ["chat_id", "message_id"]},
            "_fn": telegram_delete_message,
        },
        {
            "name": "telegram_forward_message",
            "description": "Forward a message from one Telegram chat to another.",
            "parameters": {"type": "object", "properties": {
                "chat_id": {"type": "string", "description": "Destination chat ID"},
                "from_chat_id": {"type": "string", "description": "Source chat ID"},
                "message_id": {"type": "integer", "description": "Message ID to forward"},
            }, "required": ["chat_id", "from_chat_id", "message_id"]},
            "_fn": telegram_forward_message,
        },
        {
            "name": "telegram_send_photo",
            "description": "Send a photo to a Telegram chat.",
            "parameters": {"type": "object", "properties": {
                "chat_id": {"type": "string", "description": "Target chat ID"},
                "photo": {"type": "string", "description": "URL or file_id of the photo"},
                "caption": {"type": "string", "description": "Optional photo caption"},
            }, "required": ["chat_id", "photo"]},
            "_fn": telegram_send_photo,
        },
        {
            "name": "telegram_get_chat",
            "description": "Get information about a Telegram chat.",
            "parameters": {"type": "object", "properties": {
                "chat_id": {"type": "string", "description": "Chat ID or @username"},
            }, "required": ["chat_id"]},
            "_fn": telegram_get_chat,
        },
        {
            "name": "telegram_send_poll",
            "description": "Send a poll to a Telegram chat.",
            "parameters": {"type": "object", "properties": {
                "chat_id": {"type": "string", "description": "Target chat ID"},
                "question": {"type": "string", "description": "Poll question"},
                "options": {"type": "array", "items": {"type": "string"}, "description": "List of answer options"},
            }, "required": ["chat_id", "question", "options"]},
            "_fn": telegram_send_poll,
        },
    ],
    "aws": [
        {
            "name": "s3_upload_text",
            "description": "Upload a text string as a file to S3.",
            "parameters": {"type": "object", "properties": {
                "bucket": {"type": "string", "description": "S3 bucket name"},
                "key": {"type": "string", "description": "Object key (path in bucket)"},
                "content": {"type": "string", "description": "Text content to upload"},
                "content_type": {"type": "string", "description": "MIME type (default: text/plain)"},
            }, "required": ["bucket", "key", "content"]},
            "_fn": s3_upload_text,
        },
        {
            "name": "s3_download_as_text",
            "description": "Download an S3 object and return its content as text.",
            "parameters": {"type": "object", "properties": {
                "bucket": {"type": "string", "description": "S3 bucket name"},
                "key": {"type": "string", "description": "Object key"},
            }, "required": ["bucket", "key"]},
            "_fn": s3_download_as_text,
        },
        {
            "name": "s3_delete_object",
            "description": "Delete an object from S3.",
            "parameters": {"type": "object", "properties": {
                "bucket": {"type": "string", "description": "S3 bucket name"},
                "key": {"type": "string", "description": "Object key to delete"},
            }, "required": ["bucket", "key"]},
            "_fn": s3_delete_object,
        },
        {
            "name": "s3_list_objects",
            "description": "List objects in an S3 bucket, optionally filtered by prefix.",
            "parameters": {"type": "object", "properties": {
                "bucket": {"type": "string", "description": "S3 bucket name"},
                "prefix": {"type": "string", "description": "Filter prefix (folder path)"},
                "max_keys": {"type": "integer", "description": "Maximum number of objects to return"},
            }, "required": ["bucket"]},
            "_fn": s3_list_objects,
        },
        {
            "name": "s3_list_buckets",
            "description": "List all S3 buckets in the account.",
            "parameters": {"type": "object", "properties": {}, "required": []},
            "_fn": s3_list_buckets,
        },
        {
            "name": "s3_generate_presigned_url",
            "description": "Generate a pre-signed URL for temporary access to an S3 object.",
            "parameters": {"type": "object", "properties": {
                "bucket": {"type": "string", "description": "S3 bucket name"},
                "key": {"type": "string", "description": "Object key"},
                "expiration": {"type": "integer", "description": "URL expiry in seconds (default 3600)"},
            }, "required": ["bucket", "key"]},
            "_fn": s3_generate_presigned_url,
        },
        {
            "name": "s3_copy_object",
            "description": "Copy an S3 object from one location to another.",
            "parameters": {"type": "object", "properties": {
                "source_bucket": {"type": "string", "description": "Source bucket"},
                "source_key": {"type": "string", "description": "Source object key"},
                "dest_bucket": {"type": "string", "description": "Destination bucket"},
                "dest_key": {"type": "string", "description": "Destination object key"},
            }, "required": ["source_bucket", "source_key", "dest_bucket", "dest_key"]},
            "_fn": s3_copy_object,
        },
    ],
}
