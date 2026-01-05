# CLAUDE.md

## Project
**BoothList**: BOOTH asset dashboard generator.

## Architecture
- **ETL Pipeline**: Input -> Scrape -> Normalize -> Export
- **Tech Stack**: Python, PyYAML, BeautifulSoup4, HTML/JS

## Development
- **Run**: `python3 -m boothlist.main`
- **Config**: `config.yaml`
- **Output**: `dist/`

## Key Files
- `src/boothlist/main.py`: Entry point
- `src/boothlist/scrape.py`: Metadata scraper
- `src/boothlist/normalize.py`: Data normalization
- `src/boothlist/export.py`: Catalog/Dashboard generation