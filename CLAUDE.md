# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **BoothList** project - a BOOTH asset dashboard reconstruction system that creates a searchable, analyzable, and visualizable dashboard for purchased BOOTH items (avatars, costumes, accessories, tools, etc.). The system focuses on recursive decomposition of "set products" into their sub-elements, identifying target avatars and variants.

## Architecture

The project is designed as a **Python-based ETL pipeline** that:
1. **Data Input**: Processes BOOTH purchase data from various sources (YAML, Google Sheets, manual input)
2. **Meta Extraction**: Web scrapes BOOTH item pages for metadata (name, shop, price, images)
3. **Set Decomposition**: Recursively analyzes set products to extract sub-items and avatar compatibility
4. **Data Normalization**: Creates structured catalog with items, variants, avatars, and relationships
5. **Dashboard Generation**: Produces static HTML dashboard and exports for publication

### Key Components

- **Data Processing**: `input/hitaiall.py` - Main ETL script with Google Sheets integration, web scraping, and dashboard generation
- **Input Data**: 
  - `input/booth.md` - Raw BOOTH purchase history (copy-paste format)
  - `input/booth3.yaml` - Structured purchase data with metadata
  - `datasheets/booth.yml` - Processed datasheet
- **Requirements**: `docs/requirements.md` - Comprehensive technical specification (Japanese)

### Data Models

The system works with these key entities:
- **Item**: BOOTH products with item_id, metadata, files, and target avatars
- **Variant/Subitem**: Avatar-specific components within set products
- **Avatar**: Target models (Selestia, Kikyo, Kanae, Shinano, etc.)
- **PurchaseRecord**: Usage tracking data

## Development Commands

### Running the ETL Pipeline
```bash
python input/hitaiall.py
```

This script:
- Reads from Google Sheets (configured in Config class)
- Scrapes BOOTH for item metadata (with caching)
- Generates HTML dashboard
- Can upload to GitHub (if tokens configured)

### Data Processing
- Input files are processed from `input/` directory
- Cache is stored in `booth_item_cache.json`
- Output HTML is generated as `index.html`

## Key Features

### Set Product Decomposition
The system's core innovation is **recursive set analysis**:
- Parses item descriptions and file names to identify avatar compatibility
- Extracts related item URLs and analyzes them recursively (max depth 2)
- Creates virtual sub-item IDs: `{parent_item_id}#variant:{avatar_code}:{variant_name}`
- Handles circular references with visited set tracking

### Avatar Dictionary
Supports major VRChat avatars including:
- Selestia (セレスティア)
- Kikyo (桔梗) 
- Kanae (かなえ)
- Shinano (しなの)
- Manuka (マヌカ)
- Moe (萌)
- Rurune (ルルネ)
- Hakka (薄荷)

### Dashboard Features
- Global search and filtering by avatar, type, shop, price range
- Avatar compatibility matrix
- Set product hierarchical view
- Static HTML output for GitHub Pages deployment
- Ranking system for popular avatar/costume combinations

## Configuration

Main configuration is in the `Config` class within `hitaiall.py`:
- Google Sheets integration (spreadsheet_id)
- GitHub deployment settings (currently with empty token)
- Cache file paths
- Output file names

## Important Notes

- The system is designed for **Japanese content** (BOOTH marketplace)
- Uses **web scraping** with rate limiting (1 second delays)
- Implements **caching** to avoid repeated API calls
- **No authentication required** - works with public BOOTH data only
- Built for **static deployment** (GitHub Pages compatible)

## Files to Avoid Modifying

- `input/booth.md` - Raw purchase data (large file)
- Cache files (if present) - Contain scraped metadata
- Generated HTML output - Recreated on each run

## Development Workflow

1. Update input data in `input/booth3.yaml` or configure Google Sheets
2. Run the ETL pipeline: `python input/hitaiall.py`
3. Review generated `index.html` dashboard
4. Deploy to static hosting if needed

The system is designed to be run periodically to update the dashboard with new purchases and price changes.