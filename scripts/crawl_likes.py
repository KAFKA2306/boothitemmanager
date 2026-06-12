import os
import json
import asyncio
import aiohttp
from pathlib import Path

async def fetch_like_count(session, item_id, sem):
    url = f"https://booth.pm/ja/items/{item_id}.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    async with sem:
        for attempt in range(3):
            try:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        count = data.get("wish_lists_count", 0)
                        print(f"✓ Item {item_id}: {count} likes")
                        return item_id, count
                    elif response.status == 404:
                        print(f"✗ Item {item_id}: 404 Not Found")
                        return item_id, 0
                    elif response.status == 429:
                        print(f"⚠ Item {item_id}: 429 Rate Limited. Retrying...")
                        await asyncio.sleep(5 * (attempt + 1))
                    else:
                        print(f"⚠ Item {item_id}: HTTP {response.status}")
            except Exception as e:
                print(f"⚠ Item {item_id} error: {e}")
                await asyncio.sleep(2)
        return item_id, 0

async def main():
    raw_dir = Path("input/raw")
    item_ids = [f.stem for f in raw_dir.glob("*.html")]
    print(f"Found {len(item_ids)} HTML files in input/raw/")

    cache_path = Path("data/raw/likes_cache.json")
    likes_cache = {}
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                likes_cache = json.load(f)
            print(f"Loaded {len(likes_cache)} items from cache.")
        except Exception as e:
            print("Failed to load cache:", e)

    # Filter out items that are already in cache with likes > 0
    to_crawl = [iid for iid in item_ids if iid not in likes_cache or likes_cache[iid] == 0]
    print(f"Need to crawl {len(to_crawl)} items.")

    if not to_crawl:
        print("All items are already cached.")
        return

    # Use a semaphore to limit concurrency (respect Booth rate limits)
    sem = asyncio.Semaphore(5)
    
    # Configure connector to limit total connections
    connector = aiohttp.TCPConnector(limit=5)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_like_count(session, iid, sem) for iid in to_crawl]
        
        # Process in chunks to save progress periodically
        chunk_size = 50
        for i in range(0, len(tasks), chunk_size):
            chunk = tasks[i:i+chunk_size]
            results = await asyncio.gather(*chunk)
            
            # Update cache
            for item_id, count in results:
                if count > 0:
                    likes_cache[item_id] = count
            
            # Save progress
            os.makedirs(cache_path.parent, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(likes_cache, f, ensure_ascii=False, indent=2)
            print(f"Saved progress. Total cached: {len(likes_cache)}")
            
            # Polite pause between chunks
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
