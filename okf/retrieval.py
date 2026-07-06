"""
Retrieval over an OKF bundle.

Two signals, combined:
1. TF-IDF similarity over concept text (title + description + body) -- this
   is the "search" part any RAG system needs.
2. One-hop traversal of the markdown link graph starting from the top TF-IDF
   hits -- this is what a plain chunk-and-embed RAG system loses. Because OKF
   concepts explicitly link related concepts, we can pull in the neighbors of
   a good hit even if the neighbor's own text doesn't score well on the query.

No vector DB, no external embedding model, no persistent index -- rebuilt
in-memory per query, which is plenty fast for a bundle of a few thousand
concepts. YAGNI: add a real vector index only if/when bundle size demands it.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .bundle import Bundle
from .models import Concept


@dataclass
class RetrievedConcept:
    concept: Concept
    score: float
    via_link_from: str | None  # title of the concept that linked to this one, if not a direct hit


class Retriever:
    def __init__(self, bundle: Bundle):
        self.bundle = bundle
        self.concepts: list[Concept] = bundle.load_all_concepts()
        self._by_relpath: dict[str, Concept] = {
            bundle.relative_path(c.path): c for c in self.concepts if c.path
        }
        texts = [f"{c.title} {c.description} {c.body}" for c in self.concepts]
        self._vectorizer = TfidfVectorizer(stop_words="english", max_features=20000)
        self._matrix = self._vectorizer.fit_transform(texts) if texts else None

    def search(self, query: str, top_k: int = 5, expand_links: bool = True) -> list[RetrievedConcept]:
        if not self.concepts or self._matrix is None:
            return []

        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]

        ranked_idx = scores.argsort()[::-1][:top_k]
        results: list[RetrievedConcept] = []
        seen_paths: set[str] = set()

        for idx in ranked_idx:
            if scores[idx] <= 0:
                continue
            concept = self.concepts[idx]
            relpath = self.bundle.relative_path(concept.path) if concept.path else str(idx)
            seen_paths.add(relpath)
            results.append(RetrievedConcept(concept=concept, score=float(scores[idx]), via_link_from=None))

        if expand_links:
            for r in list(results):
                neighbor_dir = r.concept.path.parent if r.concept.path else self.bundle.root
                for link in r.concept.links:
                    neighbor_path = (neighbor_dir / link).resolve()
                    try:
                        relpath = str(neighbor_path.relative_to(self.bundle.root.resolve()))
                    except ValueError:
                        continue
                    if relpath in seen_paths or relpath.endswith("index.md"):
                        continue
                    neighbor = self._by_relpath.get(relpath)
                    if neighbor:
                        seen_paths.add(relpath)
                        results.append(
                            RetrievedConcept(concept=neighbor, score=0.0, via_link_from=r.concept.title)
                        )

        return results
