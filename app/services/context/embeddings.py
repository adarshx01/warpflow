"""OpenAI embeddings for vector store."""

import logging
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

EMBEDDING_BATCH_SIZE = 2000  # OpenAI limit


async def get_embeddings(texts: list[str], api_key: str) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using OpenAI API.

    Args:
        texts: List of text strings to embed
        api_key: OpenAI API key

    Returns:
        List of embedding vectors
    """
    settings = get_settings()
    client = AsyncOpenAI(api_key=api_key)

    all_embeddings = []

    # Process in batches
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]

        response = await client.embeddings.create(
            input=batch,
            model=settings.OPENAI_EMBEDDING_MODEL,
        )

        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

        logger.debug("Generated embeddings for batch %d-%d", i, i + len(batch))

    return all_embeddings


async def get_single_embedding(text: str, api_key: str) -> list[float]:
    """Generate embedding for a single text."""
    embeddings = await get_embeddings([text], api_key)
    return embeddings[0]


def get_embedding_dimension() -> int:
    """Return the embedding dimension for the configured model."""
    settings = get_settings()
    # text-embedding-3-small has 1536 dimensions
    dimensions = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    return dimensions.get(settings.OPENAI_EMBEDDING_MODEL, 1536)
