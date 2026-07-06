"""
Bundle = the actual OKF directory on disk.

Responsible for:
- writing concept files
- maintaining index.md (directory listing / progressive disclosure)
- maintaining log.md (chronological change history)
- loading all concepts back for retrieval

Deliberately just filesystem operations -- no database. An OKF bundle IS the
storage layer, that's the whole point of the format.
"""
from __future__ import annotations

from pathlib import Path

from .models import Concept, RESERVED_FILENAMES, now_iso


class Bundle:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        if not (self.root / "log.md").exists():
            self._write_log_header()
        if not (self.root / "index.md").exists():
            self._write_root_index(doc_slugs=[])

    # ---------- writing ----------

    def write_concept(self, concept: Concept, subdir: str, filename: str) -> Path:
        target_dir = self.root / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / filename
        path.write_text(concept.to_markdown(), encoding="utf-8")
        concept.path = path
        return path

    def write_doc_index(self, subdir: str, doc_title: str, concept_files: list[str]) -> Path:
        """Per-document index.md so an agent can progressively disclose a doc's
        sections instead of reading the whole thing at once."""
        lines = [f"# {doc_title}", "", "Sections in this document:", ""]
        for fname in concept_files:
            title = fname.replace(".md", "").replace("-", " ").title()
            lines.append(f"- [{title}]({fname})")
        path = self.root / subdir / "index.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def refresh_root_index(self) -> None:
        doc_dirs = sorted(
            p.name for p in self.root.iterdir() if p.is_dir() and not p.name.startswith(".")
        )
        self._write_root_index(doc_dirs)

    def _write_root_index(self, doc_slugs: list[str]) -> None:
        lines = [
            "# Knowledge Bundle",
            "",
            "OKF v0.1 bundle produced by the Enterprise AI Knowledge Assistant.",
            "",
            "Documents:",
            "",
        ]
        for slug in doc_slugs:
            title = slug.replace("-", " ").title()
            lines.append(f"- [{title}]({slug}/index.md)")
        (self.root / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_log_header(self) -> None:
        (self.root / "log.md").write_text("# Change Log\n", encoding="utf-8")

    def append_log(self, message: str) -> None:
        date = now_iso()[:10]
        log_path = self.root / "log.md"
        content = log_path.read_text(encoding="utf-8") if log_path.exists() else "# Change Log\n"

        heading = f"## {date}"
        bullet = f"* **Update**: {message}"

        if heading in content:
            parts = content.split(heading, 1)
            new_content = parts[0] + heading + f"\n\n{bullet}\n" + parts[1].lstrip()
        else:
            new_content = content.rstrip() + f"\n\n{heading}\n\n{bullet}\n"

        log_path.write_text(new_content, encoding="utf-8")

    # ---------- reading ----------

    def load_all_concepts(self) -> list[Concept]:
        concepts = []
        for path in self.root.rglob("*.md"):
            if path.name in RESERVED_FILENAMES:
                continue
            text = path.read_text(encoding="utf-8")
            concepts.append(Concept.from_markdown(text, path=path))
        return concepts

    def relative_path(self, path: Path) -> str:
        return str(path.relative_to(self.root))
