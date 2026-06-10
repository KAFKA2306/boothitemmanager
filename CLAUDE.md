# CLAUDE.md

## Project

**BoothList**: BOOTH asset dashboard generator.

## Architecture

- **ETL Pipeline**: Input -> Scrape -> Normalize -> Export
- **Tech Stack**: Python, PyYAML, BeautifulSoup4, HTML/JS

## Development

- **Run (Bulk)**: `python3 run_bulk_pipeline.py`
- **Run (Selective)**: `python3 run_boothitemmanager2.py`
- **Build**: `task build` (Runs bulk pipeline)
- **Serve**: `task serve` (Serves from `dist/` at http://localhost:8080)
- **Config**: `config.yaml`
- **Output**: `dist/` and `api/`
- **Extract IDs**: `python3 -m boothlist.extract_ids`
  - Reads text from stdin (paste & Ctrl+D), extracts Booth IDs, and saves them to `input/YYYYMMDD.txt`.

## Key Files

- `run_bulk_pipeline.py`: Main entry for processing bulk datasets
- `run_boothitemmanager2.py`: Orchestrator for selective item crawling
- `src/boothitemmanager2/agents/api_generator.py`: Static JSON API generator
- `index.html`: Frontend dashboard (uses `api/` data)