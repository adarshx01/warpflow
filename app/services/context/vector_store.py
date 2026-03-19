"""ChromaDB vector store operations."""

import logging
from pathlib import Path
from uuid import UUID

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_chroma_client(user_id: str) -> chromadb.Client:
    """Get or create a ChromaDB client for a user."""
    settings = get_settings()
    persist_path = Path(settings.CHROMADB_PATH) / user_id
    persist_path.mkdir(parents=True, exist_ok=True)

    return chromadb.Client(
        ChromaSettings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=str(persist_path),
            anonymized_telemetry=False,
        )
    )


def _get_collection_name(user_id: str, collection_name: str) -> str:
    """Generate a unique collection name."""
    # ChromaDB collection names must be 3-63 chars, alphanumeric with underscores
    safe_name = "".join(c if c.isalnum() else "_" for c in collection_name)
    return f"u_{user_id[:8]}_{safe_name}"[:63]


class VectorStore:
    """ChromaDB-based vector store for document chunks."""

    def __init__(self, user_id: str, collection_name: str):
        self.user_id = user_id
        self.collection_name = collection_name
        self._client = _get_chroma_client(user_id)
        self._full_collection_name = _get_collection_name(user_id, collection_name)

    def _get_or_create_collection(self):
        """Get or create the ChromaDB collection."""
        return self._client.get_or_create_collection(
            name=self._full_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """
        Add documents to the vector store.

        Args:
            ids: Unique IDs for each chunk
            texts: Text content of each chunk
            embeddings: Embedding vectors for each chunk
            metadatas: Metadata dicts for each chunk
        """
        collection = self._get_or_create_collection()

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        self._client.persist()
        logger.info(
            "Added %d documents to collection %s",
            len(ids),
            self._full_collection_name,
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """
        Query the vector store for similar documents.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            where: Optional metadata filter

        Returns:
            List of results with content, metadata, and score
        """
        collection = self._get_or_create_collection()

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Convert ChromaDB results to a more user-friendly format
        output = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                output.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1 - results["distances"][0][i] if results["distances"] else 0,
                })

        return output

    def delete_by_document_id(self, document_id: str) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: The document ID to delete

        Returns:
            Number of chunks deleted
        """
        collection = self._get_or_create_collection()

        # Get IDs of chunks with this document_id
        results = collection.get(
            where={"document_id": document_id},
            include=[],
        )

        if results["ids"]:
            collection.delete(ids=results["ids"])
            self._client.persist()
            logger.info(
                "Deleted %d chunks for document %s",
                len(results["ids"]),
                document_id,
            )
            return len(results["ids"])

        return 0

    def clear(self) -> int:
        """
        Clear all documents from the collection.

        Returns:
            Number of chunks deleted
        """
        try:
            collection = self._get_or_create_collection()
            count = collection.count()

            if count > 0:
                # Get all IDs and delete
                results = collection.get(include=[])
                if results["ids"]:
                    collection.delete(ids=results["ids"])
                    self._client.persist()

            logger.info("Cleared %d chunks from collection %s", count, self._full_collection_name)
            return count

        except Exception as e:
            logger.error("Failed to clear collection: %s", e)
            return 0

    def count(self) -> int:
        """Get the number of chunks in the collection."""
        try:
            collection = self._get_or_create_collection()
            return collection.count()
        except Exception:
            return 0

    def list_documents(self) -> list[dict]:
        """
        List unique documents in the collection.

        Returns:
            List of document metadata
        """
        try:
            collection = self._get_or_create_collection()
            results = collection.get(include=["metadatas"])

            # Group by document_id
            documents = {}
            for metadata in results["metadatas"] or []:
                doc_id = metadata.get("document_id")
                if doc_id and doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "filename": metadata.get("filename", "Unknown"),
                        "total_chunks": metadata.get("total_chunks", 0),
                    }

            return list(documents.values())

        except Exception as e:
            logger.error("Failed to list documents: %s", e)
            return []
