"""
OKF v0.1 core data model.

An OKF bundle is a directory of markdown files. Each file is one "concept"
with a small YAML frontmatter block (only `type` is required) and a markdown
body. Concepts cross-link via normal markdown links.

We keep this to exactly what the spec needs -- no extra fields, no ORM,
no schema validation framework. YAGNI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re

import yaml


RESERVED_FILENAMES = {"index.md", "log.md"}


def slugify(text: str) -> str:
    """Turn a heading/title into a filesystem-safe, URL-safe slug."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "untitled"


@dataclass
class Concept:
    """A single OKF concept: one markdown file, one unit of knowledge."""

    type: str                      # required by OKF spec (e.g. "Policy", "Section")
    title: str = ""
    description: str = ""
    resource: str = ""             # pointer back to the original source
    tags: list[str] = field(default_factory=list)
    timestamp: str = ""
    body: str = ""                 # markdown body (after frontmatter)
    links: list[str] = field(default_factory=list)  # bundle-relative paths this concept links to
    path: Path | None = None       # where this concept lives inside the bundle (set on write/load)

    def to_markdown(self) -> str:
        frontmatter = {"type": self.type}
        if self.title:
            frontmatter["title"] = self.title
        if self.description:
            frontmatter["description"] = self.description
        if self.resource:
            frontmatter["resource"] = self.resource
        if self.tags:
            frontmatter["tags"] = self.tags
        if self.timestamp:
            frontmatter["timestamp"] = self.timestamp

        fm_yaml = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
        return f"---\n{fm_yaml}\n---\n\n{self.body.strip()}\n"

    @staticmethod
    def from_markdown(text: str, path: Path | None = None) -> "Concept":
        """Parse a concept file. Tolerant per spec: missing optional fields,
        unknown keys, and unknown type values are all fine."""
        fm: dict = {}
        body = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    fm = {}
                body = parts[2]

        links = re.findall(r"\[[^\]]*\]\(([^)]+\.md[^)]*)\)", body)

        return Concept(
            type=fm.get("type", "Unknown"),
            title=fm.get("title", ""),
            description=fm.get("description", ""),
            resource=fm.get("resource", ""),
            tags=fm.get("tags", []) or [],
            timestamp=fm.get("timestamp", ""),
            body=body.strip(),
            links=links,
            path=path,
        )


def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
