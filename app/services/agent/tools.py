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
)
from app.services.context.router import (
    context_upload_document, context_query, context_list_documents,
    context_delete_document, context_clear_collection, context_list_collections,
)

ServiceFn = Callable[[str, dict[str, Any]], Awaitable[dict]]

# Tools that don't require OAuth credentials (use user_id instead)
CREDENTIAL_LESS_TOOLS = {
    "ml-trainer",  # Legacy
    "data-prep",
    "supervised-train",
    "unsupervised-train",
    "model-inference",
    "context-store",
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
            "description": "List all uploaded datasets",
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
            "description": "Analyze a dataset to get column types (numeric/categorical), statistics, and missing value info. Always run this after uploading to understand your data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "ID of the dataset to analyze"},
                },
                "required": ["dataset_id"],
            },
            "_fn": ml_analyze_dataset,
        },
        {
            "name": "ml_preview_dataset",
            "description": "Get a preview of the dataset rows",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "ID of the dataset"},
                    "n_rows": {"type": "integer", "description": "Number of rows to preview (default 10)"},
                },
                "required": ["dataset_id"],
            },
            "_fn": ml_preview_dataset,
        },
        {
            "name": "ml_list_datasets",
            "description": "List all uploaded datasets",
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
            "name": "ml_train_supervised",
            "description": "Train a supervised learning model (classification or regression). Supports algorithms: logistic_regression, random_forest_classifier, svm_classifier, gradient_boosting_classifier, adaboost_classifier, catboost_classifier for classification; linear_regression, random_forest_regressor, svm_regressor, gradient_boosting_regressor, adaboost_regressor, catboost_regressor for regression.",
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
                            "gradient_boosting_regressor", "adaboost_regressor", "catboost_regressor"
                        ],
                        "description": "ML algorithm to use",
                    },
                    "target_column": {"type": "string", "description": "Target column for prediction (required)"},
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
                },
                "required": ["dataset_id", "algorithm", "target_column"],
            },
            "_fn": ml_train_supervised,
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
    ],
    "unsupervised-train": [
        {
            "name": "ml_train_unsupervised",
            "description": "Train an unsupervised learning model (clustering or dimensionality reduction). Supports algorithms: kmeans, dbscan for clustering; pca for dimensionality reduction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_id": {"type": "string", "description": "ID of the dataset to train on"},
                    "algorithm": {
                        "type": "string",
                        "enum": ["kmeans", "dbscan", "pca"],
                        "description": "ML algorithm to use",
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
                        "description": "Algorithm-specific hyperparameters (e.g., n_clusters for kmeans)",
                    },
                },
                "required": ["dataset_id", "algorithm"],
            },
            "_fn": ml_train_unsupervised,
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
    ],
    "model-inference": [
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
                        "description": "Input data as array of objects with feature values",
                    },
                },
                "required": ["model_id", "input_data"],
            },
            "_fn": ml_predict,
        },
        {
            "name": "ml_list_models",
            "description": "List all trained models available for inference",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
            "_fn": ml_list_models,
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
}
