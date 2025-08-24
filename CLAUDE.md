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

- **Design Documentation**: 
  - `docs/requirements.md` - Comprehensive technical specification (Japanese)
  - `docs/design.md` - MVP design document with concrete algorithms (Japanese)
- **Input Data Sources**: 
  - `input/booth3.yaml` - Structured purchase data with metadata (primary)
  - `input/booth.md` - Raw BOOTH purchase history (copy-paste format, large)
  - `datasheets/booth.yml` - Processed datasheet (if present)

### Data Models

The system works with these key entities:
- **Item**: BOOTH products with item_id, metadata, files, and target avatars
- **Variant/Subitem**: Avatar-specific components within set products
- **Avatar**: Target models (Selestia, Kikyo, Kanae, Shinano, etc.)
- **PurchaseRecord**: Usage tracking data

## Development Commands

This project currently has no main executable or build commands as it's in early development phase. The system is designed as a Python-based ETL pipeline with the following development workflow:

### Common Development Tasks
```bash
# Check input data structure
head -20 input/booth3.yaml

# View cache status
ls -la booth_item_cache.json

# Validate generated output
ls -la index.html catalog.yml metrics.yml

# Clean cache (force re-scraping)
rm booth_item_cache.json
```

### Data Processing Flow
1. **Input Processing**: Files from `input/` directory → normalized item list
2. **Metadata Enrichment**: Web scraping with `booth_item_cache.json` caching  
3. **Set Decomposition**: Recursive analysis (max depth 2) → virtual variants
4. **Output Generation**: `catalog.yml`, `metrics.yml`, `index.html`

## Key Features

### Set Product Decomposition
The system's core innovation is **recursive set analysis**:
- **Heuristic Detection**: Analyzes file names (e.g., "Kikyo_", "Selestia_") and item descriptions
- **Avatar Pattern Matching**: Uses dictionary of known avatars with aliases (Japanese/English)
- **Recursive Analysis**: Extracts related item URLs and analyzes them (currently depth 1 in MVP, max depth 2 planned)
- **Virtual ID Generation**: Creates unique IDs like `{parent_item_id}#variant:{avatar_code}:{variant_name}`
- **Confidence Scoring**: Filename patterns (0.9), explicit text (0.95), contextual mentions (0.8)
- **Circular Reference Prevention**: Tracks visited items to avoid infinite loops

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
- Mizuki (瑞希)

### Dashboard Features
- Global search and filtering by avatar, type, shop, price range
- Avatar compatibility matrix
- Set product hierarchical view
- Static HTML output for GitHub Pages deployment
## Configuration & Architecture Details

### MVP Scope (Current Implementation)
- **Input Processing**: Text/CSV/YAML normalization from `input/` directory
- **Metadata Scraping**: Public BOOTH pages with single-layer YAML cache
- **Set Decomposition**: Heuristic analysis with depth-1 recursion
- **Static Output**: Dashboard SPA with client-side search/filtering
- **Avatar Support**: ~9 major VRChat avatars with Japanese/English aliases

### Implementation Notes
- **Target Audience**: Japanese VRChat community (BOOTH marketplace)
- **Data Format**: YAML-centric with fallbacks for various input formats

## Files to Avoid Modifying

- `input/booth.md` - Raw purchase data (large file)
- Cache files (if present) - Contain scraped metadata
- Generated HTML output - Recreated on each run

## Development Workflow

### Planned Development Structure (from docs/tasks.md)
The project is organized into development milestones:
- **M1**: ETL pipeline foundation and catalog generation
- **M2**: Set decomposition (depth 1) and aggregation  
- **M3**: Dashboard (static SPA) and publication

### Planned Module Structure
```
src/boothlist/
├── input_loader.py    # md/csv/yml import & normalization
├── scrape.py          # metadata extraction, rate control, caching
├── extract.py         # set decomposition: text/filenames/related items
├── normalize.py       # schema formatting, alias integration
├── aggregate.py       # metrics generation
└── export.py          # catalog.yml/metrics.yml output
```

### Development Patterns
- **Iterative Processing**: System handles partial failures gracefully via caching
- **Cache Management**: Delete `booth_item_cache.json` to force full re-scraping
- **Data Validation**: Check logs for scraping failures or parsing errors
- **Testing**: Verify set decomposition results in generated catalog.yml

### Key Algorithms to Understand
- **Item ID Extraction**: Multiple URL pattern matching for BOOTH links
- **Set Detection**: File naming patterns + text analysis for avatar compatibility  
- **Recursive Expansion**: Related item discovery with circular reference prevention
- **Virtual ID Schema**: `{item_id}#variant:{avatar}:{slug}` for unique subitem identification