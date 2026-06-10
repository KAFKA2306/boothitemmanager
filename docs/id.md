# ID Based Fetching

## Strategy
1. **Fetch**: GET `https://booth.pm/ja/items/{id}`.
2. **Scrape**: Priority: JSON-LD > OG Meta > DOM.
3. **Cache**: Store result in `booth_item_cache.json` with timestamp.
4. **Retry**: Exponential backoff/rate limiting.