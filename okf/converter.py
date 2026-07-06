"""
Convert an uploaded document into OKF concepts and write them into a bundle.

Pipeline: parse into sections -> one concept per section -> add frontmatter
-> add cross-links (to siblings and back to the parent doc) -> write to disk
-> update index.md / log.md.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .bundle import Bundle
from .models import Concept, now_iso, slugify
from .parsers import parse_document, Section


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "is", "are",
    "be", "this", "that", "with", "as", "by", "at", "from", "it", "shall",
    "will", "may", "must", "which", "who", "these", "those", "any", "all",
    "not", "if", "then", "such", "into", "each", "other", "including", "its",
}


def _auto_tags(text: str, max_tags: int = 5) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", text.lower())
    words = [w for w in words if w not in _STOPWORDS]
    common = [w for w, _ in Counter(words).most_common(max_tags)]
    return common


def _auto_description(text: str, max_chars: int = 200) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut + "..."


def convert_document(
    bundle: Bundle,
    file_path: Path,
    original_filename: str,
    doc_type: str = "Document",
) -> list[Concept]:
    """Parse `file_path`, write one OKF concept per section into the bundle
    under a folder named after the document, and refresh index.md / log.md.
    Returns the concepts written."""

    sections: list[Section] = parse_document(file_path)
    doc_title = Path(original_filename).stem.replace("_", " ").replace("-", " ").title()
    doc_slug = slugify(doc_title)

    concepts: list[Concept] = []
    filenames: list[str] = []

    # first pass: build concepts + filenames so we can cross-link siblings
    seen_slugs: dict[str, int] = {}
    for section in sections:
        base_slug = slugify(section.heading)
        seen_slugs[base_slug] = seen_slugs.get(base_slug, 0) + 1
        slug = base_slug if seen_slugs[base_slug] == 1 else f"{base_slug}-{seen_slugs[base_slug]}"
        filenames.append(f"{slug}.md")

    for i, (section, fname) in enumerate(zip(sections, filenames)):
        body_lines = [section.body] if section.body else []

        related_links = []
        if i > 0:
            related_links.append(f"[{sections[i-1].heading}]({filenames[i-1]})")
        if i < len(sections) - 1:
            related_links.append(f"[{sections[i+1].heading}]({filenames[i+1]})")
        related_links.append(f"[{doc_title} overview](index.md)")

        if related_links:
            body_lines.append("\n## Related\n\n" + "\n".join(f"- {l}" for l in related_links))

        body = "\n".join(body_lines).strip() or section.heading

        concept = Concept(
            type=doc_type,
            title=section.heading,
            description=_auto_description(section.body or section.heading),
            resource=original_filename,
            tags=_auto_tags(section.body or section.heading),
            timestamp=now_iso(),
            body=body,
        )
        bundle.write_concept(concept, subdir=doc_slug, filename=fname)
        concepts.append(concept)

    bundle.write_doc_index(doc_slug, doc_title, filenames)
    bundle.refresh_root_index()
    bundle.append_log(
        f"Ingested \"{original_filename}\" as {len(concepts)} {doc_type} concept(s) "
        f"under `{doc_slug}/`."
    )

    return concepts
