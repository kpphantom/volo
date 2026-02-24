"""
VOLO — RAG Pipeline
Retrieval-Augmented Generation for enhanced context.
Uses vector embeddings for semantic search across memories,
documents, and conversation history.
"""

import os
import logging
import hashlib
from typing import Optional
from datetime import datetime

logger = logging.getLogger("volo.rag")


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.
    - Embeds documents/memories using OpenAI embeddings
    - Stores vectors in pgvector
    - Retrieves relevant context for each query
    Falls back to keyword search when embeddings unavailable.
    """

    def __init__(self):
        self._openai = None
        self._documents: list[dict] = []  # In-memory fallback
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dim = 1536

    @property
    def openai_client(self):
        if self._openai is None:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if api_key and len(api_key) > 10:
                try:
                    from openai import OpenAI
                    self._openai = OpenAI(api_key=api_key)
                except Exception:
                    pass
        return self._openai

    async def embed_text(self, text: str) -> Optional[list[float]]:
        """Generate embedding vector for text."""
        if not self.openai_client:
            return None

        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            return None

    async def index_document(
        self,
        content: str,
        metadata: dict = None,
        doc_id: str = None,
    ) -> dict:
        """Index a document for RAG retrieval."""
        if not doc_id:
            doc_id = hashlib.md5(content.encode()).hexdigest()

        embedding = await self.embed_text(content)

        doc = {
            "id": doc_id,
            "content": content,
            "metadata": metadata or {},
            "embedding": embedding,
            "indexed_at": datetime.utcnow().isoformat(),
        }
        self._documents.append(doc)
        return {"id": doc_id, "indexed": True, "has_embedding": embedding is not None}

    async def search(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.5,
    ) -> list[dict]:
        """
        Search indexed documents by semantic similarity.
        Falls back to keyword matching if embeddings unavailable.
        """
        query_embedding = await self.embed_text(query)

        if query_embedding:
            return self._vector_search(query_embedding, limit, min_score)
        else:
            return self._keyword_search(query, limit)

    def _vector_search(
        self,
        query_embedding: list[float],
        limit: int,
        min_score: float,
    ) -> list[dict]:
        """Cosine similarity search."""
        import math

        results = []
        for doc in self._documents:
            if not doc.get("embedding"):
                continue

            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_embedding, doc["embedding"]))
            norm_q = math.sqrt(sum(a * a for a in query_embedding))
            norm_d = math.sqrt(sum(a * a for a in doc["embedding"]))
            similarity = dot / (norm_q * norm_d) if norm_q and norm_d else 0

            if similarity >= min_score:
                results.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": round(similarity, 4),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _keyword_search(self, query: str, limit: int) -> list[dict]:
        """Fallback keyword-based search."""
        query_words = set(query.lower().split())
        results = []

        for doc in self._documents:
            content_lower = doc["content"].lower()
            matches = sum(1 for w in query_words if w in content_lower)
            if matches > 0:
                score = matches / len(query_words)
                results.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": round(score, 4),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def clear(self):
        """Clear all indexed documents."""
        self._documents = []

    def get_stats(self) -> dict:
        return {
            "total_documents": len(self._documents),
            "with_embeddings": sum(1 for d in self._documents if d.get("embedding")),
            "embedding_model": self.embedding_model,
            "openai_configured": self.openai_client is not None,
        }


# Singleton
rag = RAGPipeline()
