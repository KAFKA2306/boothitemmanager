# Requirements

## Goal
Reconstruct BoothList dashboard for visualizing purchase data.

## Scope
- Input: Purchase history (YAML/CSV)
- Process: Scrape metadata, recursively decompose sets, normalize data.
- Output: `catalog.yml`, `metrics.yml`, `index.html`.

## Key Features
- **Set Decomposition**: Recursively extracting sub-items from sets (e.g., full avatar sets).
- **Normalization**: Standardizing avatar names and item types.
- **Dashboard**: Static HTML for searching and filtering.

## Data Model
- **Item**: ID, name, price, files, targets (avatars).
- **Variant**: Sub-components of an item.
- **Avatar**: Normalized target entity (e.g., Kikyo).