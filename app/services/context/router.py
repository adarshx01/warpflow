"""FastAPI router and tool functions for Context Store service."""

import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import User, ContextCollection, ContextDocument
from app.auth.utils import get_current_user
from app.services.storage import upload_file, delete_file
from app.services.storage.s3_storage import decode_base64_content
from app.services.context.schemas import (
    UploadDocumentRequest,
    QueryRequest,
    DeleteDocumentRequest,
    ClearCollectionRequest,
    CreateCollectionRequest,
    ListDocumentsRequest,
    ExecuteRequest,
    DocumentUploadResponse,
    QueryResponse,
    DocumentListResponse,
    CollectionListResponse,
    DeleteResponse,
    ClearResponse,
)
from app.services.context.embeddings import get_embeddings, get_single_embedding
from app.services.context.pdf_processor import extract_text, chunk_text, get_chunk_metadata
from app.services.context.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context-store", tags=["Context Store"])


# ─────────────────────────────────────────────────────────────────────────────
# HTTP Endpoints (for direct API access)
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/collections", response_model=dict)
async def create_collection_endpoint(
    request: CreateCollectionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new collection."""
    # Check if collection already exists
    existing = await _get_collection_by_name(db, request.name, user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Collection already exists")

    collection = ContextCollection(
        owner_id=user.id,
        name=request.name,
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)

    return {
        "id": str(collection.id),
        "name": collection.name,
        "document_count": 0,
        "chunk_count": 0,
        "created_at": collection.created_at.isoformat(),
    }


@router.get("/collections", response_model=CollectionListResponse)
async def list_collections_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List user's collections."""
    result = await context_list_collections(str(user.id), {}, db)
    return result


@router.delete("/collections/{collection_name}", response_model=ClearResponse)
async def delete_collection_endpoint(
    collection_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a collection and all its documents."""
    result = await context_clear_collection(
        str(user.id),
        {"collection_name": collection_name},
        db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Delete the collection from database
    collection = await _get_collection_by_name(db, collection_name, user.id)
    if collection:
        await db.delete(collection)
        await db.commit()

    return result


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document_endpoint(
    request: UploadDocumentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a document to a collection."""
    result = await context_upload_document(
        str(user.id),
        request.model_dump(),
        db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/documents/{collection_name}", response_model=DocumentListResponse)
async def list_documents_endpoint(
    collection_name: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List documents in a collection."""
    result = await context_list_documents(
        str(user.id),
        {"collection_name": collection_name},
        db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/documents/{collection_name}/{document_id}", response_model=DeleteResponse)
async def delete_document_endpoint(
    collection_name: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a document from a collection."""
    result = await context_delete_document(
        str(user.id),
        {"collection_name": collection_name, "document_id": document_id},
        db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Query a collection for relevant documents."""
    result = await context_query(
        str(user.id),
        request.model_dump(),
        db,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/execute")
async def execute_endpoint(
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Execute a context store operation (for workflow integration)."""
    operations = {
        "upload_document": context_upload_document,
        "query": context_query,
        "list_documents": context_list_documents,
        "delete_document": context_delete_document,
        "clear_collection": context_clear_collection,
        "list_collections": context_list_collections,
    }

    op_fn = operations.get(request.operation)
    if not op_fn:
        raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")

    result = await op_fn(str(user.id), request.params, db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Tool Functions (for AI Agent integration)
# Signature: async def fn(user_id: str, params: dict, db: AsyncSession = None) -> dict
# ─────────────────────────────────────────────────────────────────────────────


async def context_upload_document(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Upload a PDF or text document to the vector store."""
    try:
        collection_name = params["collection_name"]
        file_content = decode_base64_content(params["file_content"])
        filename = params["filename"]
        file_type = params["file_type"]
        chunk_size = params.get("chunk_size", 500)
        chunk_overlap = params.get("chunk_overlap", 50)

        # Extract text from document
        text = extract_text(file_content, file_type)
        if not text.strip():
            return {"error": "No text content could be extracted from the document"}

        # Chunk the text
        chunks = chunk_text(text, chunk_size, chunk_overlap)
        if not chunks:
            return {"error": "Document produced no chunks"}

        # Generate embeddings (local model - no API key needed)
        embeddings = await get_embeddings(chunks)

        # Generate document ID and create metadata
        document_id = str(uuid4())
        ids = [f"{document_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            get_chunk_metadata(chunk, i, document_id, filename, len(chunks))
            for i, chunk in enumerate(chunks)
        ]

        # Store in vector database
        vector_store = VectorStore(user_id, collection_name)
        vector_store.add_documents(ids, chunks, embeddings, metadatas)

        # Upload original file to S3 for backup (optional - skip if S3 not configured)
        s3_path = None
        settings = get_settings()
        if settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY:
            try:
                s3_path = upload_file(
                    user_id=UUID(user_id),
                    category="documents",
                    file_id=UUID(document_id),
                    content=file_content,
                    extension=file_type,
                    content_type=_get_content_type(file_type),
                )
            except Exception as e:
                logger.warning("S3 upload skipped (optional): %s", e)

        # Ensure collection exists in database and update counts
        collection = await _get_or_create_collection(db, collection_name, UUID(user_id))

        # Create document record
        doc = ContextDocument(
            id=UUID(document_id),
            collection_id=collection.id,
            filename=filename,
            file_type=file_type,
            chunk_count=len(chunks),
            s3_path=s3_path,
        )
        db.add(doc)

        # Update collection counts
        collection.document_count += 1
        collection.chunk_count += len(chunks)
        await db.commit()

        return {
            "document_id": document_id,
            "filename": filename,
            "chunk_count": len(chunks),
            "collection_name": collection_name,
        }

    except Exception as e:
        logger.error("Failed to upload document: %s", e)
        return {"error": str(e)}


async def context_query(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Search the vector store for relevant context using semantic similarity."""
    try:
        collection_name = params["collection_name"]
        query_text = params["query_text"]
        top_k = params.get("top_k", 5)

        # Generate query embedding (local model - no API key needed)
        query_embedding = await get_single_embedding(query_text)

        # Query vector store
        vector_store = VectorStore(user_id, collection_name)
        results = vector_store.query(query_embedding, top_k)

        return {"results": results}

    except Exception as e:
        logger.error("Failed to query: %s", e)
        return {"error": str(e)}


async def context_list_documents(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """List all documents in a vector store collection."""
    try:
        collection_name = params["collection_name"]

        # Get from vector store
        vector_store = VectorStore(user_id, collection_name)
        documents = vector_store.list_documents()

        return {"documents": documents}

    except Exception as e:
        logger.error("Failed to list documents: %s", e)
        return {"error": str(e)}


async def context_delete_document(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Remove a document from the vector store."""
    try:
        collection_name = params["collection_name"]
        document_id = params["document_id"]

        # Delete from vector store
        vector_store = VectorStore(user_id, collection_name)
        deleted_count = vector_store.delete_by_document_id(document_id)

        # Delete from database
        stmt = select(ContextDocument).where(ContextDocument.id == UUID(document_id))
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()

        if doc:
            # Delete S3 file
            if doc.s3_path:
                delete_file(doc.s3_path)

            # Update collection counts
            collection = await _get_collection_by_name(db, collection_name, UUID(user_id))
            if collection:
                collection.document_count = max(0, collection.document_count - 1)
                collection.chunk_count = max(0, collection.chunk_count - doc.chunk_count)

            await db.delete(doc)
            await db.commit()

        return {"success": True, "deleted_count": deleted_count}

    except Exception as e:
        logger.error("Failed to delete document: %s", e)
        return {"error": str(e)}


async def context_clear_collection(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """Clear all documents from a vector store collection."""
    try:
        collection_name = params["collection_name"]

        # Clear vector store
        vector_store = VectorStore(user_id, collection_name)
        deleted_count = vector_store.clear()

        # Delete documents from database
        collection = await _get_collection_by_name(db, collection_name, UUID(user_id))
        if collection:
            stmt = select(ContextDocument).where(ContextDocument.collection_id == collection.id)
            result = await db.execute(stmt)
            docs = result.scalars().all()

            for doc in docs:
                if doc.s3_path:
                    delete_file(doc.s3_path)
                await db.delete(doc)

            collection.document_count = 0
            collection.chunk_count = 0
            await db.commit()

        return {
            "success": True,
            "collection_name": collection_name,
            "deleted_count": deleted_count,
        }

    except Exception as e:
        logger.error("Failed to clear collection: %s", e)
        return {"error": str(e)}


async def context_list_collections(user_id: str, params: dict[str, Any], db: AsyncSession = None) -> dict:
    """List user's collections."""
    try:
        stmt = select(ContextCollection).where(
            ContextCollection.owner_id == UUID(user_id)
        ).order_by(ContextCollection.created_at.desc())

        result = await db.execute(stmt)
        collections = result.scalars().all()

        return {
            "collections": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "document_count": c.document_count,
                    "chunk_count": c.chunk_count,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in collections
            ]
        }

    except Exception as e:
        logger.error("Failed to list collections: %s", e)
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────


async def _get_collection_by_name(db: AsyncSession, name: str, user_id: UUID) -> ContextCollection | None:
    """Get collection by name and user ID."""
    stmt = select(ContextCollection).where(
        ContextCollection.name == name,
        ContextCollection.owner_id == user_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_or_create_collection(db: AsyncSession, name: str, user_id: UUID) -> ContextCollection:
    """Get or create a collection."""
    collection = await _get_collection_by_name(db, name, user_id)
    if not collection:
        collection = ContextCollection(owner_id=user_id, name=name)
        db.add(collection)
        await db.flush()
    return collection


def _get_content_type(file_type: str) -> str:
    """Get MIME type for file type."""
    content_types = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "md": "text/markdown",
    }
    return content_types.get(file_type, "application/octet-stream")
