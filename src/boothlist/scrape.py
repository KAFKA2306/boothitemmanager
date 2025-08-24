"""BOOTH metadata scraper with caching and rate limiting."""

import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ItemMetadata:
    """Metadata extracted from BOOTH item page."""
    item_id: int
    name: Optional[str] = None
    shop_name: Optional[str] = None
    creator_id: Optional[str] = None
    image_url: Optional[str] = None
    current_price: Optional[int] = None
    description_excerpt: Optional[str] = None
    canonical_url: Optional[str] = None
    files: list = None
    updated_at: Optional[str] = None
    scraped_at: Optional[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.files is None:
            self.files = []
        if self.scraped_at is None:
            self.scraped_at = datetime.now().isoformat()


class BoothScraper:
    """Scrapes BOOTH item metadata with caching and rate limiting."""
    
    def __init__(self, cache_file: str = 'booth_item_cache.json', rate_limit: float = 1.0):
        """Initialize scraper with cache file and rate limit (seconds between requests)."""
        self.cache_file = Path(cache_file)
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.cache = self._load_cache()
        
        # Common headers to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load existing cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                logger.info(f"Loaded cache with {len(cache)} entries from {self.cache_file}")
                return cache
            except Exception as e:
                logger.error(f"Error loading cache file {self.cache_file}: {e}")
        
        return {}
    
    def _save_cache(self):
        """Save cache to file."""
        try:
            # Create directory if it doesn't exist
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved cache with {len(self.cache)} entries to {self.cache_file}")
        except Exception as e:
            logger.error(f"Error saving cache file {self.cache_file}: {e}")
    
    def _rate_limit_wait(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _extract_metadata(self, html: str, item_id: int) -> ItemMetadata:
        """Extract metadata from BOOTH item page HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        metadata = ItemMetadata(item_id=item_id)
        
        # Item name - multiple selectors as fallback
        name_selectors = [
            'h1.item-name',
            '.item-name h1',
            '.item-header h1',
            'h1[data-tracking-label="item_name"]',
            '.item-detail-title h1'
        ]
        
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem:
                metadata.name = name_elem.get_text(strip=True)
                break
        
        # Shop name
        shop_selectors = [
            '.shop-name a',
            '.shop-name',
            '.booth-user-name a',
            '.user-name a'
        ]
        
        for selector in shop_selectors:
            shop_elem = soup.select_one(selector)
            if shop_elem:
                metadata.shop_name = shop_elem.get_text(strip=True)
                # Try to extract creator_id from URL
                href = shop_elem.get('href', '')
                creator_match = re.search(r'/([^/]+)/?$', href)
                if creator_match:
                    metadata.creator_id = creator_match.group(1)
                break
        
        # Current price
        price_selectors = [
            '.price .yen',
            '.item-price .yen',
            '.current-price .yen',
            '.price-tag .yen'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract number from price text (remove ¥ and commas)
                price_match = re.search(r'[\d,]+', price_text)
                if price_match:
                    try:
                        metadata.current_price = int(price_match.group().replace(',', ''))
                        break
                    except ValueError:
                        continue
        
        # Check for free items
        if metadata.current_price is None:
            free_indicators = soup.find_all(string=re.compile(r'無料|free|¥0', re.IGNORECASE))
            if free_indicators:
                metadata.current_price = 0
        
        # Main image
        image_selectors = [
            '.item-image img',
            '.main-image img',
            '.product-image img',
            '.item-header img'
        ]
        
        for selector in image_selectors:
            img_elem = soup.select_one(selector)
            if img_elem:
                src = img_elem.get('src') or img_elem.get('data-src')
                if src:
                    metadata.image_url = urljoin(f"https://booth.pm/ja/items/{item_id}", src)
                    break
        
        # Description excerpt
        desc_selectors = [
            '.item-description .markdown',
            '.item-description',
            '.description .markdown',
            '.item-detail-description'
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                desc_text = desc_elem.get_text(strip=True)
                # Limit to first 200 characters
                metadata.description_excerpt = desc_text[:200] + '...' if len(desc_text) > 200 else desc_text
                break
        
        # Files (from download section if visible)
        file_selectors = [
            '.download-list .file-name',
            '.file-list .file-name',
            '.attachment-list .file-name'
        ]
        
        files = []
        for selector in file_selectors:
            file_elems = soup.select(selector)
            for elem in file_elems:
                filename = elem.get_text(strip=True)
                if filename:
                    files.append(filename)
        
        metadata.files = files
        metadata.canonical_url = f"https://booth.pm/ja/items/{item_id}"
        
        return metadata
    
    def scrape_item(self, item_id: int, force_refresh: bool = False) -> ItemMetadata:
        """Scrape metadata for a single item with caching."""
        cache_key = str(item_id)
        
        # Check cache first
        if not force_refresh and cache_key in self.cache:
            cached_data = self.cache[cache_key]
            # Check if cached data has error - retry if it's an old error
            if 'error' in cached_data:
                cached_time = datetime.fromisoformat(cached_data.get('scraped_at', '1970-01-01'))
                # Retry after 24 hours for errors
                if (datetime.now() - cached_time).total_seconds() < 24 * 3600:
                    logger.debug(f"Using cached error for item {item_id}")
                    return ItemMetadata(**cached_data)
            else:
                logger.debug(f"Using cached data for item {item_id}")
                return ItemMetadata(**cached_data)
        
        # Apply rate limiting
        self._rate_limit_wait()
        
        # Scrape the item
        url = f"https://booth.pm/ja/items/{item_id}"
        
        try:
            logger.debug(f"Scraping item {item_id}: {url}")
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                metadata = self._extract_metadata(response.text, item_id)
                logger.info(f"Successfully scraped item {item_id}: {metadata.name}")
                
                # Cache successful result
                self.cache[cache_key] = asdict(metadata)
                self._save_cache()
                
                return metadata
            
            elif response.status_code == 404:
                error_msg = f"Item {item_id} not found (404)"
                logger.warning(error_msg)
                
                # Cache 404 errors to avoid repeated requests
                error_metadata = ItemMetadata(item_id=item_id, error=error_msg)
                self.cache[cache_key] = asdict(error_metadata)
                self._save_cache()
                
                return error_metadata
            
            else:
                error_msg = f"HTTP {response.status_code} for item {item_id}"
                logger.warning(error_msg)
                
                # Cache other HTTP errors temporarily
                error_metadata = ItemMetadata(item_id=item_id, error=error_msg)
                self.cache[cache_key] = asdict(error_metadata)
                self._save_cache()
                
                return error_metadata
        
        except requests.exceptions.Timeout:
            error_msg = f"Timeout scraping item {item_id}"
            logger.warning(error_msg)
            
            error_metadata = ItemMetadata(item_id=item_id, error=error_msg)
            self.cache[cache_key] = asdict(error_metadata)
            self._save_cache()
            
            return error_metadata
        
        except Exception as e:
            error_msg = f"Error scraping item {item_id}: {str(e)}"
            logger.error(error_msg)
            
            error_metadata = ItemMetadata(item_id=item_id, error=error_msg)
            self.cache[cache_key] = asdict(error_metadata)
            self._save_cache()
            
            return error_metadata
    
    def scrape_items(self, item_ids: list, force_refresh: bool = False) -> Dict[int, ItemMetadata]:
        """Scrape metadata for multiple items."""
        results = {}
        
        logger.info(f"Scraping {len(item_ids)} items (force_refresh={force_refresh})")
        
        for i, item_id in enumerate(item_ids):
            logger.info(f"Scraping item {i+1}/{len(item_ids)}: {item_id}")
            metadata = self.scrape_item(item_id, force_refresh)
            results[item_id] = metadata
        
        logger.info(f"Completed scraping {len(item_ids)} items")
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        error_entries = sum(1 for entry in self.cache.values() if 'error' in entry)
        success_entries = total_entries - error_entries
        
        return {
            'total_entries': total_entries,
            'success_entries': success_entries,
            'error_entries': error_entries,
            'cache_file': str(self.cache_file),
            'cache_file_exists': self.cache_file.exists()
        }


def main():
    """Test the scraper with sample data."""
    logging.basicConfig(level=logging.INFO)
    
    scraper = BoothScraper()
    
    # Test with a few sample items
    test_item_ids = [3984867, 6893042, 5589706]  # From booth3.yaml
    
    results = scraper.scrape_items(test_item_ids)
    
    print("\nScraping results:")
    for item_id, metadata in results.items():
        if metadata.error:
            print(f"  {item_id}: ERROR - {metadata.error}")
        else:
            print(f"  {item_id}: {metadata.name} by {metadata.shop_name} (¥{metadata.current_price})")
    
    print(f"\nCache stats: {scraper.get_cache_stats()}")


if __name__ == '__main__':
    main()