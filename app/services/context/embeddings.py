"""Local embeddings using sentence-transformers for vector store."""

import logging
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import get_settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Get or initialize the embedding model (singleton)."""
    global _model
    if _model is None:
        settings = get_settings()
        model_name = settings.LOCAL_EMBEDDING_MODEL
        logger.info("Loading embedding model: %s", model_name)
        _model = SentenceTransformer(model_name)
        logger.info("Embedding model loaded successfully")
    return _model


async def get_embeddings(texts: list[str], api_key: str = None) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using local model.

    Args:
        texts: List of text strings to embed
        api_key: Ignored (kept for API compatibility)

    Returns:
        List of embedding vectors
    """
    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return embeddings.tolist()


async def get_single_embedding(text: str, api_key: str = None, task_type: str = None) -> list[float]:
    """
    Generate embedding for a single text.

    Args:
        text: Text to embed
        api_key: Ignored (kept for API compatibility)
        task_type: Ignored (kept for API compatibility)

    Returns:
        Embedding vector
    """
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
    return embedding.tolist()


def get_embedding_dimension() -> int:
    """Return the embedding dimension for the configured model."""
    settings = get_settings()
    # Common model dimensions
    dimensions = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "paraphrase-MiniLM-L6-v2": 384,
        "multi-qa-MiniLM-L6-cos-v1": 384,
    }
    return dimensions.get(settings.LOCAL_EMBEDDING_MODEL, 384)
