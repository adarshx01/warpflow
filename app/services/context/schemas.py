"""Pydantic schemas for Context Store service."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# Request schemas
class UploadDocumentRequest(BaseModel):
    collection_name: str = Field(..., description="Name of the collection to add to")
    file_content: str = Field(..., description="Base64-encoded file content")
    filename: str = Field(..., description="Original filename")
    file_type: Literal["pdf", "txt", "md"] = Field(..., description="File format")
    chunk_size: int = Field(default=500, description="Characters per chunk")
    chunk_overlap: int = Field(default=50, description="Overlap between chunks")


class QueryRequest(BaseModel):
    collection_name: str = Field(..., description="Name of the collection to search")
    query_text: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results to return")


class DeleteDocumentRequest(BaseModel):
    collection_name: str = Field(..., description="Name of the collection")
    document_id: str = Field(..., description="ID of the document to delete")


class ClearCollectionRequest(BaseModel):
    collection_name: str = Field(..., description="Name of the collection to clear")


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., description="Collection name")


class ListDocumentsRequest(BaseModel):
    collection_name: str = Field(..., description="Name of the collection")


class ExecuteRequest(BaseModel):
    operation: Literal[
        "upload_document", "query", "list_documents", "delete_document", "clear_collection", "list_collections"
    ]
    params: dict[str, Any]


# Response schemas
class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    collection_name: str


class QueryResult(BaseModel):
    content: str
    metadata: dict[str, Any]
    score: float


class QueryResponse(BaseModel):
    results: list[QueryResult]


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    total_chunks: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]


class CollectionInfo(BaseModel):
    id: str
    name: str
    document_count: int
    chunk_count: int
    created_at: str
    updated_at: str


class CollectionListResponse(BaseModel):
    collections: list[CollectionInfo]


class DeleteResponse(BaseModel):
    success: bool
    deleted_count: int


class ClearResponse(BaseModel):
    success: bool
    collection_name: str
    deleted_count: int
