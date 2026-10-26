"""Vector embedding, disk cache, and hybrid retrieval index for ClauseLens AI."""

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import ollama
import config
from ingest import Chunk

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "could", "did", "do", "does", "doing",
    "down", "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most",
    "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or",
    "other", "our", "ours", "ourselves", "out", "over", "own", "s", "same", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "we", "were", "what", "when",
    "where", "which", "while", "who", "whom", "why", "will", "with", "would", "you", "your"
}


class PolicyIndex:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.chunks: List[Chunk] = []
        self.embeddings: Optional[np.ndarray] = None  # shape (N, D)
        self.client = ollama.Client(host=config.OLLAMA_HOST, timeout=config.LLM_TIMEOUT)

    def _file_content_hash(self, content_str: str) -> str:
        return hashlib.sha256(content_str.encode("utf-8")).hexdigest()

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embeds a batch of texts using nomic-embed-text via Ollama."""
        if not texts:
            return np.empty((0, 768), dtype=np.float32)
        
        # Batch requests in chunks of 16 to avoid payload limits
        all_vecs = []
        batch_size = 16
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            res = self.client.embed(model=config.EMBED_MODEL, input=batch)
            for emb in res.embeddings:
                all_vecs.append(emb)

        arr = np.array(all_vecs, dtype=np.float32)
        # Normalize
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        return arr / np.maximum(norms, 1e-9)

    def add_document(self, doc_name: str, raw_content: str, chunks: List[Chunk]):
        """Adds document chunks to the index with disk caching by content hash."""
        if not chunks:
            return

        doc_hash = self._file_content_hash(raw_content)
        cache_path = os.path.join(self.cache_dir, f"{doc_hash}.npz")
        meta_path = os.path.join(self.cache_dir, f"{doc_hash}.json")

        if os.path.exists(cache_path) and os.path.exists(meta_path):
            try:
                npz = np.load(cache_path)
                doc_embeddings = npz["embeddings"]
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_chunks = json.load(f)
                cached_chunks = [Chunk(**m) for m in meta_chunks]
                self._append_data(cached_chunks, doc_embeddings)
                return
            except Exception:
                # If cache is corrupt, regenerate
                pass

        # Compute embeddings
        texts_to_embed = [c.embedding_text for c in chunks]
        doc_embeddings = self.embed_texts(texts_to_embed)

        # Save to disk cache
        try:
            np.savez_compressed(cache_path, embeddings=doc_embeddings)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump([c.to_dict() for c in chunks], f, indent=2)
        except Exception:
            pass

        self._append_data(chunks, doc_embeddings)

    def _append_data(self, chunks: List[Chunk], new_embeddings: np.ndarray):
        self.chunks.extend(chunks)
        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])

    def query(self, question: str, top_k: int = config.TOP_K) -> List[Tuple[Chunk, float]]:
        """Performs hybrid retrieval (cosine similarity + keyword boost).
        
        Returns list of (Chunk, hybrid_score) sorted descending by score.
        """
        if not self.chunks or self.embeddings is None or len(self.chunks) == 0:
            return []

        # 1. Embed query
        q_res = self.client.embed(model=config.EMBED_MODEL, input=question)
        q_vec = np.array(q_res.embeddings[0], dtype=np.float32)
        q_norm = q_vec / max(np.linalg.norm(q_vec), 1e-9)

        # 2. Cosine similarity
        cosine_scores = np.dot(self.embeddings, q_norm)

        # 3. Keyword overlap boost
        q_tokens = [
            w.lower() for w in re.findall(r"\b[a-zA-Z0-9_-]+\b", question)
            if w.lower() not in STOPWORDS and len(w) > 2
        ]

        scored_chunks: List[Tuple[Chunk, float]] = []
        for idx, (chunk, cos_score) in enumerate(zip(self.chunks, cosine_scores)):
            chunk_lower = chunk.text.lower()
            if q_tokens:
                matches = sum(1 for token in q_tokens if token in chunk_lower)
                kw_boost = 0.08 * (matches / len(q_tokens))
            else:
                kw_boost = 0.0

            hybrid_score = float(cos_score + kw_boost)
            scored_chunks.append((chunk, hybrid_score))

        # Sort descending
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    def clear(self):
        """Clears memory index."""
        self.chunks = []
        self.embeddings = None
