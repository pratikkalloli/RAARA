"""Pure local deterministic TF/hash embedding used by offline evaluation."""
from __future__ import annotations

import hashlib
import math
import re


class DeterministicTfidfHashEmbedding:
    """Offline lexical baseline; scores are not comparable to OpenAI embeddings."""

    model_name = "deterministic-tfidf-hash-v1"

    def __init__(self, dimensions: int = 2048):
        if dimensions < 64:
            raise ValueError("dimensions must be at least 64")
        self.dimensions, self.document_frequency, self.document_count = dimensions, {}, 0

    @staticmethod
    def _terms(text: str) -> list[str]:
        words = re.findall(r"[a-z0-9]+", text.casefold())
        return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]

    def fit_documents(self, texts: list[str]) -> None:
        self.document_count = len(texts)
        for text in texts:
            for term in set(self._terms(text)):
                self.document_frequency[term] = self.document_frequency.get(term, 0) + 1

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        result = []
        for text in texts:
            vector = [0.0] * self.dimensions
            counts: dict[str, int] = {}
            for term in self._terms(text):
                counts[term] = counts.get(term, 0) + 1
            for term, count in counts.items():
                idx = int.from_bytes(hashlib.blake2b(term.encode(), digest_size=8).digest(), "big") % self.dimensions
                idf = math.log((1 + self.document_count) / (1 + self.document_frequency.get(term, 0))) + 1
                vector[idx] += (1 + math.log(count)) * idf
            norm = math.sqrt(sum(x * x for x in vector))
            result.append([x / norm for x in vector] if norm else vector)
        return result
