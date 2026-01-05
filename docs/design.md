# Design

## Architecture
- **Input**: YAML/CSV/Text in `input/`.
- **Scraper**: Fetch metadata from `booth.pm/ja/items/{id}`. Cache in YAML/JSON.
- **Extractor**: Heuristic analysis of filenames and text to find sub-items and targets.
- **Normalizer**: Standardize data types and avatar references.
- **Exporter**: Generate static site and optional YAML reports.

## Key Logic
- **Recursive Extraction**: Depth-limited search for related items.
- **Avatar Recognition**: Dictionary-based matching of names and aliases.
- **File Parsing**: Version and potential target extraction from filenames.
