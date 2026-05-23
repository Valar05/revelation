#!/usr/bin/env python3
"""Validate and index Revelation corpus source files."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "generated" / "corpus"
MANIFEST_PATH = CORPUS_DIR / "revelation_source_manifest.json"
INDEX_DIR = CORPUS_DIR / "index"
EXTRACTED_DIR = CORPUS_DIR / "texts" / "extracted"

STOPWORDS = {
    "about", "after", "again", "against", "also", "among", "because", "before", "being",
    "between", "could", "every", "from", "have", "into", "more", "must", "shall", "should",
    "that", "their", "there", "these", "they", "this", "those", "through", "under", "until",
    "were", "what", "when", "where", "which", "while", "with", "would", "your", "unto",
    "upon", "will", "them", "then", "than", "thee", "thou", "said", "lord", "god",
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def source_path(source: dict) -> Path:
    return ROOT / source["local_path"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "windows-1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_gutenberg_boilerplate(text: str) -> str:
    start_match = re.search(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .*?\*\*\*", text, re.IGNORECASE)
    if start_match:
        text = text[start_match.end():]
    end_match = re.search(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .*?\*\*\*", text, re.IGNORECASE)
    if end_match:
        text = text[:end_match.start()]
    return text


def clean_usfm_text(text: str) -> str:
    text = re.sub(r"\\id\s+\S+", "", text)
    text = re.sub(r"\\toc\d?\s+", "\n", text)
    text = re.sub(r"\\[a-z][a-z0-9*]*\s*", " ", text)
    return text


def html_to_text(raw: str) -> str:
    parser = TextExtractor()
    parser.feed(raw)
    return parser.text()


def pdf_to_text(path: Path) -> str:
    if shutil.which("pdftotext") is None:
        return ""
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    output = EXTRACTED_DIR / f"{path.stem}.txt"
    subprocess.run(
        ["pdftotext", "-layout", str(path), str(output)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if not output.exists():
        return ""
    return clean_text(output.read_text(encoding="utf-8", errors="replace"))


def iter_text_sections(path: Path) -> list[tuple[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = pdf_to_text(path)
        return [(path.name, text)] if text else []
    if suffix == ".zip":
        sections: list[tuple[str, str]] = []
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if not n.endswith("/")]
            for name in sorted(names):
                lower = name.lower()
                if not lower.endswith((".txt", ".usfm", ".sfm", ".html", ".htm", ".vpl", ".xml")):
                    continue
                raw = decode_bytes(archive.read(name))
                if lower.endswith((".html", ".htm")):
                    raw = html_to_text(raw)
                if lower.endswith((".usfm", ".sfm")):
                    raw = clean_usfm_text(raw)
                cleaned = clean_text(raw)
                if cleaned:
                    sections.append((name, cleaned))
        return sections
    raw = decode_bytes(path.read_bytes())
    if path.name.lower().endswith(".txt") and "PROJECT GUTENBERG" in raw[:5000].upper():
        raw = strip_gutenberg_boilerplate(raw)
    if suffix in {".html", ".htm"}:
        raw = html_to_text(raw)
    cleaned = clean_text(raw)
    return [(path.name, cleaned)] if cleaned else []


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]{2,}", text)


def count_words(text: str) -> int:
    return len(words(text))


def keywords(text: str, limit: int = 12) -> list[str]:
    terms = [term.lower().strip("-'") for term in words(text)]
    terms = [term for term in terms if len(term) > 3 and term not in STOPWORDS]
    return [term for term, _ in Counter(terms).most_common(limit)]


def split_long_para(paragraph: str, max_words: int) -> list[str]:
    tokens = paragraph.split()
    if len(tokens) <= max_words:
        return [paragraph]
    return [" ".join(tokens[i:i + max_words]) for i in range(0, len(tokens), max_words)]


def make_chunks(text: str, max_words: int = 520) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    for paragraph in paragraphs:
        for part in split_long_para(paragraph, max_words):
            part_words = count_words(part)
            if current and current_words + part_words > max_words:
                chunks.append("\n\n".join(current).strip())
                current = []
                current_words = 0
            current.append(part)
            current_words += part_words
    if current:
        chunks.append("\n\n".join(current).strip())
    return [chunk for chunk in chunks if count_words(chunk) >= 20]


def validate() -> int:
    manifest = load_manifest()
    errors: list[str] = []
    seen: set[str] = set()
    for source in manifest.get("sources", []):
        source_id = source.get("id", "<missing>")
        if source_id in seen:
            errors.append(f"duplicate source id: {source_id}")
        seen.add(source_id)
        for key in ("id", "title", "category", "source_url", "local_path", "license", "active"):
            if key not in source:
                errors.append(f"{source_id}: missing {key}")
        if source.get("active"):
            path = source_path(source)
            if not path.exists():
                errors.append(f"{source_id}: missing file {source['local_path']}")
            elif path.stat().st_size == 0:
                errors.append(f"{source_id}: empty file {source['local_path']}")
    if errors:
        print("CORPUS_VALIDATE_FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("CORPUS_VALIDATE_OK")
    return 0


def build_gap_report(inventory: list[dict]) -> str:
    stored_unindexed = [item for item in inventory if item["extraction_status"] != "indexed"]
    lines = [
        "# Revelation Corpus Gaps",
        "",
        "This report is generated by `tools/revelation_corpus_tools.py index`.",
        "",
        "## Extraction Gaps",
        "",
    ]
    if stored_unindexed:
        for item in stored_unindexed:
            lines.append(f"- `{item['id']}` is downloaded but not text-indexed: {item['extraction_status']}.")
    else:
        lines.append("- No extraction gaps detected.")
    lines.extend([
        "",
        "## Content Gaps",
        "",
        "- No active SCP-style anomaly case corpus is included. SCP Wiki remains inactive because CC BY-SA would add attribution and share-alike obligations.",
        "- Public-domain weird fiction is now included for cosmic-horror texture and anomaly-investigation structure, but it should remain subordinate to Revelation's religious and institutional frame.",
        "- The active religious corpus is English translation only. It supports motifs and symbolic structures, but not original-language Hebrew, Aramaic, Greek, or Arabic analysis.",
        "- The active procedural corpus covers incident command, emergency operations, HAZWOPER posture, small-unit doctrine, responder stress, and decision-making under pressure, but does not yet cover laboratory chain-of-custody, hospital triage, or long-term psychological aftercare in depth.",
        "- Character voice still needs project-authored exemplars. The current corpus can anchor situations and institutional wording, but it will not by itself teach Brooks, Torah, or Institute staff dialogue.",
        "",
        "## Recommended Next Sources",
        "",
        "- U.S. government laboratory, evidence, and chain-of-custody procedures for artifact handling and Institute research reports.",
        "- U.S. government public-health and hospital emergency guidance for triage, family notification, psychological first aid, and return-to-duty decisions.",
        "- Project-authored sample transcripts and after-action reports under the Revelation license to lock in voice without importing copyleft fiction.",
    ])
    return "\n".join(lines) + "\n"


def build_index() -> int:
    manifest = load_manifest()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    chunk_records: list[dict] = []
    for source in manifest.get("sources", []):
        if not source.get("active"):
            continue
        path = source_path(source)
        if not path.exists() or path.stat().st_size == 0:
            raise SystemExit(f"missing active source file: {source['local_path']}")
        sections = iter_text_sections(path)
        indexed_words = 0
        indexed_chunks = 0
        for section_name, text in sections:
            for chunk in make_chunks(text):
                indexed_chunks += 1
                indexed_words += count_words(chunk)
                chunk_records.append({
                    "chunk_id": f"{source['id']}:{indexed_chunks:05d}",
                    "source_id": source["id"],
                    "title": source["title"],
                    "category": source["category"],
                    "section": section_name,
                    "license": source["license"],
                    "keywords": keywords(chunk),
                    "text": chunk,
                })
        if path.suffix.lower() == ".pdf" and not sections:
            extraction_status = "stored_pdf_requires_pdftotext"
        elif indexed_chunks == 0:
            extraction_status = "stored_no_indexable_text"
        else:
            extraction_status = "indexed"
        entries.append({
            "id": source["id"],
            "title": source["title"],
            "category": source["category"],
            "license": source["license"],
            "source_url": source["source_url"],
            "download_url": source.get("download_url", ""),
            "local_path": source["local_path"],
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "indexed_text_words": indexed_words,
            "indexed_chunks": indexed_chunks,
            "extraction_status": extraction_status,
        })
    output = {
        "schema_version": 1,
        "project": manifest.get("project", "Revelation"),
        "source_count": len(entries),
        "chunk_count": len(chunk_records),
        "sources": entries,
    }
    (INDEX_DIR / "source_inventory.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    with (INDEX_DIR / "chunks.jsonl").open("w", encoding="utf-8") as handle:
        for record in chunk_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    (INDEX_DIR / "corpus_gaps.md").write_text(build_gap_report(entries), encoding="utf-8")
    print(f"CORPUS_INDEX_OK sources={len(entries)} chunks={len(chunk_records)} path={INDEX_DIR}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["validate", "index"])
    args = parser.parse_args()
    if args.command == "validate":
        return validate()
    return build_index()


if __name__ == "__main__":
    raise SystemExit(main())
