# Input Formats

## Supported Formats
- **YAML**: `booth_purchases` array with `id`, `name`, `category`, etc.
- **Markdown**: Extracts URLs (`items/{id}`).
- **CSV**: Columns for `item_id`, `url`, etc.

## Processing
All inputs are deduped by `item_id`.