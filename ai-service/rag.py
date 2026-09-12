"""
Lightweight Hybrid RAG for Clinevo Smart Inbox AI Service.

Implements page-aware evidence retrieval:
- PDF pages → page-aware chunks
- Lexical/BM25-style retrieval
- Optional vector/embedding retrieval (when available)
- Combine + rerank results
- Preserve page-level metadata

No external vector database required.
"""
import math
import re
from collections import Counter
from typing import List, Optional

from models import PageResult


class Chunk:
    """Page-aware text chunk with metadata."""
    def __init__(self, text, source_type, source_id, page, chunk_index,
                 start_char=0, end_char=0):
        self.text = text
        self.source_type = source_type
        self.source_id = source_id
        self.page = page
        self.chunk_index = chunk_index
        self.start_char = start_char
        self.end_char = end_char
        self.score = 0.0

    def to_evidence(self):
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "page": self.page,
            "text": self.text[:500],
            "chunk_index": self.chunk_index,
            "score": round(self.score, 4),
        }


class HybridRAG:
    """BM25-based retrieval with page-aware chunking."""
    def __init__(self, chunk_size=500, chunk_overlap=100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunks: List[Chunk] = []
        self.idf: dict = {}
        self.avg_dl: float = 0

    def index_pages(self, pages, source_type="PDF", source_id="document"):
        self.chunks = []
        for page in pages:
            page_chunks = self._chunk_text(page.text, page.page, source_type, source_id)
            self.chunks.extend(page_chunks)
        self._compute_bm25_stats()

    def index_text(self, text, source_type="PDF", source_id="document", page=1):
        self.chunks = self._chunk_text(text, page, source_type, source_id)
        self._compute_bm25_stats()

    def _chunk_text(self, text, page, source_type, source_id):
        chunks = []
        if not text or not text.strip():
            return chunks
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current = ""
        idx = 0
        start = 0
        for sent in sentences:
            if len(current) + len(sent) < self.chunk_size:
                current += " " + sent if current else sent
            else:
                if current.strip():
                    chunks.append(Chunk(current.strip(), source_type, source_id,
                                       page, idx, start, start + len(current)))
                    idx += 1
                if len(current) > self.chunk_overlap:
                    current = current[-self.chunk_overlap:] + " " + sent
                else:
                    current = sent
                start += len(current)
        if current.strip():
            chunks.append(Chunk(current.strip(), source_type, source_id,
                               page, idx, start, start + len(current)))
        return chunks

    def _compute_bm25_stats(self):
        if not self.chunks:
            return
        tokenized = [self._tokenize(c.text) for c in self.chunks]
        dl = [len(t) for t in tokenized]
        self.avg_dl = sum(dl) / len(dl) if dl else 1
        df = Counter()
        for tokens in tokenized:
            for token in set(tokens):
                df[token] += 1
        n = len(self.chunks)
        self.idf = {t: math.log((n - f + 0.5) / (f + 0.5) + 1) for t, f in df.items()}

    def _tokenize(self, text):
        return re.findall(r'\b[a-z0-9]+\b', text.lower())

    def _bm25_score(self, query_tokens, doc_tokens, k1=1.5, b=0.75):
        if not doc_tokens or not self.avg_dl:
            return 0.0
        doc_len = len(doc_tokens)
        tf = Counter(doc_tokens)
        score = 0.0
        for token in query_tokens:
            if token in self.idf:
                term_freq = tf.get(token, 0)
                num = term_freq * (k1 + 1)
                den = term_freq + k1 * (1 - b + b * doc_len / self.avg_dl)
                score += self.idf[token] * num / den
        return score

    def retrieve(self, query, top_k=5):
        if not self.chunks:
            return []
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.chunks[:top_k]
        for chunk in self.chunks:
            doc_tokens = self._tokenize(chunk.text)
            chunk.score = self._bm25_score(query_tokens, doc_tokens)
        sorted_chunks = sorted(self.chunks, key=lambda c: c.score, reverse=True)
        results = [c for c in sorted_chunks if c.score > 0][:top_k]
        if not results:
            results = sorted_chunks[:top_k]
        return results

    def get_evidence_context(self, query, top_k=3):
        chunks = self.retrieve(query, top_k)
        if not chunks:
            return ""
        parts = [f"[Page {c.page}] {c.text}" for c in chunks]
        return "\n\n".join(parts)
