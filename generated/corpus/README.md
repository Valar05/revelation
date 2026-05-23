# Revelation Corpus

This folder stores the license-screened source library for Revelation narrative generation.

Active corpus sources should be public domain, U.S. federal government works, CC0, or explicitly approved permissive/attribution sources. SCP Wiki material is listed only as inactive reference until the project deliberately accepts CC BY-SA attribution and share-alike obligations.

## Layout

- `revelation_source_manifest.json` records provenance, licenses, source URLs, download URLs, and local paths.
- `texts/` contains direct text or HTML downloads used by the generator/indexer.
- `source_docs/` contains PDFs, zips, and other source packages.
- `licenses/` is reserved for copied license notices or source-specific notes when needed.
- `index/` contains generated lookup files derived from active corpus sources.

## Workflow

1. Add or update sources in `revelation_source_manifest.json`.
2. Download active source files to their `local_path`.
3. Run `python tools/revelation_corpus_tools.py validate`.
4. Run `python tools/revelation_corpus_tools.py index` after source files are present.

Generated room/event prose should use these sources as anchors for motifs, circumstances, procedures, and symbolic structures, not as bulk quotation.
