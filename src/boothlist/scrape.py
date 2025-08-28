"""BOOTH metadata scraper with caching and rate limiting."""

import json
import time
import random
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ItemMetadata:
    """Metadata extracted from BOOTH item page - Enhanced per boothid.md spec."""
    item_id: int
    name: Optional[str] = None
    shop_name: Optional[str] = None
    creator_id: Optional[str] = None
    image_url: Optional[str] = None  # Absolute URL
    current_price: Optional[int] = None  # JPY, 0 for free items
    description_excerpt: Optional[str] = None  # ~200 chars
    canonical_path: str = None  # /ja/items/{item_id} format
    files: list = None  # List of filenames if available
    scraped_at: Optional[str] = None  # ISO8601 timestamp
    page_updated_at: Optional[str] = None  # ISO8601 if available from JSON-LD
    related_item_ids: list = None  # For recursive analysis
    error: Optional[str] = None  # Error message if scraping failed
    
    def __post_init__(self):
        if self.files is None:
            self.files = []
        if self.related_item_ids is None:
            self.related_item_ids = []
        if self.scraped_at is None:
            self.scraped_at = datetime.now().isoformat()
        if self.canonical_path is None:
            self.canonical_path = f"/ja/items/{self.item_id}"


class BoothScraper:
    """Scrapes BOOTH item metadata with caching and rate limiting."""
    
    def __init__(self, cache_file: str = 'booth_item_cache.json', rate_limit: float = 1.0):
        """Initialize scraper with cache file and rate limit (seconds between requests)."""
        self.cache_file = Path(cache_file)
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.cache = self._load_cache()
        
        # Enhanced headers per boothid.md specification  
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
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
    
    def _get_with_retry(self, url: str, max_retries: int = 3) -> requests.Response:
        """Make HTTP request with exponential backoff retry logic per boothid.md spec."""
        base_delays = [1.0, 2.0, 4.0]  # Base delays in seconds
        
        for attempt in range(max_retries):
            try:
                # Enforce rate limiting (minimum 1 second between requests)
                self._rate_limit_wait()
                
                logger.debug(f"Attempt {attempt + 1}/{max_retries} for {url}")
                response = requests.get(url, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    return response
                elif response.status_code in [429, 503]:  # Rate limited or service unavailable
                    if attempt < max_retries - 1:
                        delay = base_delays[attempt] + random.uniform(-0.2, 0.2)  # Add jitter
                        logger.warning(f"Rate limited (HTTP {response.status_code}), retrying in {delay:.1f}s")
                        time.sleep(delay)
                        continue
                else:
                    # Other HTTP errors, return immediately
                    return response
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delays[attempt] + random.uniform(-0.2, 0.2)
                    logger.warning(f"Request timeout, retrying in {delay:.1f}s")
                    time.sleep(delay)
                    continue
                else:
                    # Final attempt failed due to timeout
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delays[attempt] + random.uniform(-0.2, 0.2)
                    logger.warning(f"Request failed with {str(e)}, retrying in {delay:.1f}s")
                    time.sleep(delay)
                    continue
                else:
                    raise
        
        # Should not reach here, but return last response if available
        return response
    
    def _parse_json_ld(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract JSON-LD structured data from page."""
        try:
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and '@type' in data:
                        return data
                    elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                        return data[0]
        except (json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Error parsing JSON-LD: {e}")
        return None
    
    def _parse_og_tags(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract Open Graph meta tags."""
        og_data = {}
        og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
        for tag in og_tags:
            property_name = tag.get('property', '')[3:]  # Remove 'og:' prefix
            content = tag.get('content')
            if property_name and content:
                og_data[property_name] = content
        return og_data
    
    def _pick_name(self, soup: BeautifulSoup, og_data: Dict[str, str]) -> Optional[str]:
        """Extract name with prioritized approach: OG -> DOM fallback."""
        # Priority 1: OG title
        if og_data.get('title'):
            return og_data['title'].strip()
        
        # Priority 2: DOM selectors with multiple candidates
        name_selectors = [
            'h1.item-name',
            'h1.u-tpg-title1', 
            'h1[itemprop="name"]',
            '.item-name h1',
            '.item-header h1',
            'h1[data-tracking-label="item_name"]'
        ]
        
        for selector in name_selectors:
            elem = soup.select_one(selector)
            if elem:
                name = elem.get_text(strip=True)
                if name:
                    return name
        
        # Final fallback to og:title again
        return og_data.get('title')
    
    def _pick_shop_name(self, soup: BeautifulSoup, og_data: Dict[str, str]) -> Optional[str]:
        """Extract shop name with multiple selector fallbacks."""
        shop_selectors = [
            'a.shop-name',
            'div.u-text-ellipsis > a',
            'a[itemprop="author"]',
            '.shop-name',
            '.booth-user-name a',
            '.user-name a'
        ]
        
        for selector in shop_selectors:
            elem = soup.select_one(selector)
            if elem:
                shop_name = elem.get_text(strip=True)
                if shop_name:
                    return shop_name
        
        # Fallback to OG site name
        return og_data.get('site_name')
    
    def _pick_creator_id(self, soup: BeautifulSoup, response_url: str) -> Optional[str]:
        """Extract creator_id from shop URLs and subdomains."""
        # Method 1: Extract from shop links in page
        shop_link_selectors = [
            'a.shop-name',
            'div.u-text-ellipsis > a',
            'a[itemprop="author"]',
            '.booth-user-name a'
        ]
        
        for selector in shop_link_selectors:
            elem = soup.select_one(selector)
            if elem:
                href = elem.get('href', '')
                # Pattern: https://{sub}.booth.pm
                subdomain_match = re.search(r'https://([^.]+)\.booth\.pm', href)
                if subdomain_match:
                    return subdomain_match.group(1)
                
                # Pattern: /shop/{creator}
                shop_match = re.search(r'/shop/([^/?]+)', href)
                if shop_match:
                    return shop_match.group(1)
        
        # Method 2: Extract from response URL subdomain
        parsed_url = urlparse(response_url)
        if parsed_url.hostname and parsed_url.hostname.endswith('.booth.pm'):
            subdomain = parsed_url.hostname.split('.')[0]
            if subdomain != 'booth':  # Not main domain
                return subdomain
        
        return None
    
    def _pick_price(self, soup: BeautifulSoup, og_data: Dict[str, str], json_ld: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Extract price with JSON-LD support and enhanced detection."""
        
        # Priority 1: JSON-LD structured data (highest priority for accuracy)
        if json_ld:
            try:
                # Handle schema.org Product with offers
                offers = json_ld.get('offers')
                if offers:
                    # Handle single offer
                    if isinstance(offers, dict):
                        price = offers.get('price')
                        if price is not None:
                            try:
                                price_value = int(float(str(price).replace(',', '')))
                                logger.debug(f"Extracted price from JSON-LD single offer: {price_value}")
                                return price_value
                            except (ValueError, TypeError):
                                pass
                        
                        # Handle price range with lowPrice/highPrice
                        low_price = offers.get('lowPrice')
                        high_price = offers.get('highPrice')
                        if low_price is not None:
                            try:
                                price_value = int(float(str(low_price).replace(',', '')))
                                logger.debug(f"Extracted price from JSON-LD lowPrice: {price_value}")
                                return price_value
                            except (ValueError, TypeError):
                                pass
                    
                    # Handle array of offers
                    elif isinstance(offers, list) and len(offers) > 0:
                        first_offer = offers[0]
                        if isinstance(first_offer, dict):
                            price = first_offer.get('price')
                            if price is not None:
                                try:
                                    price_value = int(float(str(price).replace(',', '')))
                                    logger.debug(f"Extracted price from JSON-LD offer array: {price_value}")
                                    return price_value
                                except (ValueError, TypeError):
                                    pass
            except Exception as e:
                logger.debug(f"Error parsing JSON-LD price: {e}")
        
        # Priority 2: OG price amount with currency handling  
        og_price = og_data.get('price:amount')
        if og_price:
            try:
                # Handle various price formats including currency symbols
                price_text = str(og_price).strip()
                # Remove currency symbols and extract numbers
                price_match = re.search(r'[\d,]+', price_text)
                if price_match:
                    price_value = int(price_match.group().replace(',', ''))
                    # Only return 0 if explicitly marked as free
                    if price_value == 0 and re.search(r'無料|Free|free', price_text, re.IGNORECASE):
                        return 0
                    elif price_value > 0:
                        logger.debug(f"Extracted price from OG data: {price_value}")
                        return price_value
            except (ValueError, TypeError):
                pass
        
        # Priority 3: Enhanced DOM selectors with modern BOOTH structure
        price_selectors = [
            # Traditional selectors
            'div.price',
            'span[itemprop="price"]', 
            '.price .yen',
            '.item-price .yen',
            '.current-price .yen',
            '.price-tag .yen',
            # Generic selectors for modern BOOTH structure
            'div:contains("¥")',  # Any div containing yen symbol
            '*:contains("¥")',    # Any element containing yen symbol
        ]
        
        for selector in price_selectors:
            if 'contains' in selector:
                # Use more specific search for yen-containing elements
                elems = soup.find_all(lambda tag: tag.string and '¥' in tag.get_text())
                for elem in elems:
                    price_text = elem.get_text(strip=True)
                    
                    # Skip if this looks like unrelated content (too long)
                    if len(price_text) > 50:
                        continue
                    
                    # Extract numeric price with yen symbol
                    price_match = re.search(r'¥\s*([\d,]+)', price_text)
                    if price_match:
                        try:
                            price_value = int(price_match.group(1).replace(',', ''))
                            # Only treat as free if explicitly marked
                            if price_value == 0 and re.search(r'無料|Free|フリー', price_text, re.IGNORECASE):
                                return 0
                            elif price_value > 0:
                                logger.debug(f"Extracted price from DOM search: {price_value}")
                                return price_value
                        except ValueError:
                            continue
            else:
                elem = soup.select_one(selector)
                if elem:
                    price_text = elem.get_text(strip=True)
                    
                    # Extract numeric price
                    price_match = re.search(r'¥\s*([\d,]+)', price_text)
                    if price_match:
                        try:
                            price_value = int(price_match.group(1).replace(',', ''))
                            # Only treat as free if explicitly marked  
                            if price_value == 0 and re.search(r'無料|Free|フリー', price_text, re.IGNORECASE):
                                return 0
                            elif price_value > 0:
                                logger.debug(f"Extracted price from selector {selector}: {price_value}")
                                return price_value
                        except ValueError:
                            continue
                    
                    # Fallback numeric extraction
                    price_match = re.search(r'[\d,]+', price_text)
                    if price_match:
                        try:
                            price_value = int(price_match.group().replace(',', ''))
                            if price_value > 0:
                                logger.debug(f"Extracted price from fallback numeric: {price_value}")
                                return price_value
                        except ValueError:
                            continue
        
        # Priority 4: Explicit free item detection only (reduced scope)
        free_detection_selectors = [
            '.item-description',
            '.item-detail',
            '.item-header'
        ]
        
        for selector in free_detection_selectors:
            elem = soup.select_one(selector)
            if elem:
                content_text = elem.get_text(strip=True)
                # Only detect as free if explicitly stated with specific patterns
                if re.search(r'\b(無料|Free|フリー|0円)\b', content_text, re.IGNORECASE):
                    logger.debug(f"Detected free item from content: {selector}")
                    return 0
        
        logger.debug("No price found using any extraction method")
        return None
    
    def _pick_image(self, soup: BeautifulSoup, og_data: Dict[str, str], base_url: str) -> Optional[str]:
        """Extract image with enhanced fallback chain and quality optimization."""
        # Priority 1: OG image (often high quality)
        if og_data.get('image'):
            og_image_url = urljoin(base_url, og_data['image'])
            # Remove /c/{W}x{H}/ segments to get original quality
            return self._normalize_image_quality(og_image_url)
        
        # Priority 2: Enhanced DOM selectors with quality preferences
        image_selectors = [
            # BOOTH-specific selectors (updated)
            'img.market-item-image',
            'img.market-item-detail-image', 
            'div.item-image img',
            'div.main-image img',
            '.image-container img',
            '.product-image img:first-child',
            '.item-gallery img:first-child',
            '.booth-image img',
            'img.item-image',
            'img.main-image',
            # Generic high-quality selectors
            'img[itemprop="image"]',
            'img[class*="main"]',
            'img[class*="primary"]',
            'img[class*="hero"]',
            'img[class*="banner"]',
            # Fallback selectors
            '.item-detail img:first-child',
            'main img:first-child',
            'article img:first-child'
        ]
        
        # Track best image found
        best_image = None
        best_priority = -1
        
        for i, selector in enumerate(image_selectors):
            img_elem = soup.select_one(selector)
            if img_elem:
                # Check multiple src attributes with priority for original quality
                src = (img_elem.get('data-original') or  # Highest quality first
                       img_elem.get('src') or 
                       img_elem.get('data-src') or 
                       img_elem.get('data-lazy-src'))
                
                if src:
                    full_url = urljoin(base_url, src)
                    
                    # Quality scoring - prefer larger images
                    quality_score = self._score_image_quality(full_url, img_elem)
                    priority_score = len(image_selectors) - i  # Earlier selectors get higher priority
                    total_score = quality_score + (priority_score * 10)
                    
                    if total_score > best_priority:
                        best_image = full_url
                        best_priority = total_score
        
        # Normalize image quality if found
        if best_image:
            return self._normalize_image_quality(best_image)
        
        return None
    
    def _pick_description(self, soup: BeautifulSoup, og_data: Dict[str, str]) -> Optional[str]:
        """Extract description excerpt (~200 chars)."""
        # Priority 1: OG description
        if og_data.get('description'):
            desc = og_data['description'].strip()
            return desc[:200] + '...' if len(desc) > 200 else desc
        
        # Priority 2: DOM description areas
        desc_selectors = [
            '.item-description .markdown',
            '.item-description',
            '.description .markdown', 
            '.item-detail-description',
            '.booth-description',
            '.item-body'
        ]
        
        for selector in desc_selectors:
            elem = soup.select_one(selector)
            if elem:
                # Remove script and style content
                for script in elem(['script', 'style']):
                    script.decompose()
                
                desc_text = elem.get_text(strip=True)
                if desc_text:
                    # Compress whitespace and newlines
                    desc_text = re.sub(r'\s+', ' ', desc_text)
                    return desc_text[:200] + '...' if len(desc_text) > 200 else desc_text
        
        return None
    
    def _pick_files(self, soup: BeautifulSoup) -> List[str]:
        """Extract file names if visible (optional)."""
        file_selectors = [
            '.download-list .file-name',
            '.file-list .file-name',
            '.attachment-list .file-name',
            '.download-item .filename',
            '.file-item .name'
        ]
        
        files = []
        for selector in file_selectors:
            file_elems = soup.select(selector)
            for elem in file_elems:
                filename = elem.get_text(strip=True)
                if filename:
                    files.append(filename)
        
        return files
    
    def _extract_related_item_ids(self, soup: BeautifulSoup) -> List[int]:
        """Extract related item IDs from page content for recursive analysis per pximg.md spec."""
        related_ids = []
        
        # Enhanced search in multiple content areas including HTML links
        content_selectors = [
            '.item-description',
            '.item-detail-description', 
            '.booth-description',
            '.item-body',
            '.markdown',  # Markdown content areas
            '.related-items',  # Explicit related items sections
        ]
        
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                # Extract from both text content and href attributes
                content_text = elem.get_text()
                
                # Extract item IDs from URLs in text: items/(\d+)
                item_id_matches = re.findall(r'items/(\d+)', content_text)
                for match in item_id_matches:
                    try:
                        related_id = int(match)
                        if 1_000_000 <= related_id <= 99_999_999 and related_id not in related_ids:
                            related_ids.append(related_id)
                    except ValueError:
                        continue
                
                # Also check href attributes in links
                links = elem.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    link_matches = re.findall(r'items/(\d+)', href)
                    for match in link_matches:
                        try:
                            related_id = int(match)
                            if 1_000_000 <= related_id <= 99_999_999 and related_id not in related_ids:
                                related_ids.append(related_id)
                        except ValueError:
                            continue
        
        logger.debug(f"Extracted {len(related_ids)} related item IDs: {related_ids[:5]}{'...' if len(related_ids) > 5 else ''}")
        return related_ids
    
    def _score_image_quality(self, url: str, img_elem) -> int:
        """Score image quality based on URL patterns and attributes."""
        score = 0
        
        # Size indicators in URL
        if re.search(r'\d{3,4}x\d{3,4}', url):
            size_match = re.search(r'(\d{3,4})x(\d{3,4})', url)
            if size_match:
                width = int(size_match.group(1))
                score += min(width // 100, 10)  # Higher score for larger images
        
        # Quality indicators in URL
        if 'original' in url.lower():
            score += 15
        elif 'large' in url.lower():
            score += 10
        elif 'medium' in url.lower():
            score += 5
        
        # File extension preferences
        if url.lower().endswith('.jpg') or url.lower().endswith('.jpeg'):
            score += 3
        elif url.lower().endswith('.png'):
            score += 5
        elif url.lower().endswith('.webp'):
            score += 4
        
        # Element attributes
        width = img_elem.get('width')
        height = img_elem.get('height')
        if width and width.isdigit():
            score += min(int(width) // 100, 5)
        if height and height.isdigit():
            score += min(int(height) // 100, 5)
        
        return score
    
    def _normalize_image_quality(self, url: str) -> str:
        """Normalize image URL to get original quality by removing resize segments."""
        if not url:
            return url
            
        # BOOTH image quality normalization per pximg.md specification
        if 'booth.pximg.net' in url or 'booth.pm' in url:
            # Remove /c/{W}x{H}/ segments to get original quality
            # Pattern: /c/1200x1200/ -> remove entirely
            normalized_url = re.sub(r'/c/\d+x\d+/', '/', url)
            logger.debug(f"Normalized image URL: {url} -> {normalized_url}")
            return normalized_url
        
        return url
    
    def _extract_metadata(self, html: str, item_id: int, response_url: str) -> ItemMetadata:
        """Enhanced metadata extraction per boothid.md specification."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Parse structured data
        json_ld = self._parse_json_ld(soup)
        og_data = self._parse_og_tags(soup)
        
        # Extract metadata using prioritized approach
        name = self._pick_name(soup, og_data)
        shop_name = self._pick_shop_name(soup, og_data)
        creator_id = self._pick_creator_id(soup, response_url)
        current_price = self._pick_price(soup, og_data, json_ld)
        image_url = self._pick_image(soup, og_data, response_url)
        description_excerpt = self._pick_description(soup, og_data)
        files = self._pick_files(soup)
        related_item_ids = self._extract_related_item_ids(soup)
        
        # Extract page_updated_at from JSON-LD if available
        page_updated_at = None
        if json_ld:
            date_modified = json_ld.get('dateModified') or json_ld.get('datePublished')
            if date_modified:
                page_updated_at = date_modified
        
        return ItemMetadata(
            item_id=item_id,
            name=name,
            shop_name=shop_name,
            creator_id=creator_id,
            image_url=image_url,
            current_price=current_price,
            description_excerpt=description_excerpt,
            canonical_path=f"/ja/items/{item_id}",
            files=files,
            page_updated_at=page_updated_at,
            related_item_ids=related_item_ids
        )
    
    def scrape_item(self, item_id: int, force_refresh: bool = False) -> ItemMetadata:
        """Scrape metadata for a single item with caching."""
        cache_key = str(item_id)
        
        # Check cache first
        if not force_refresh and cache_key in self.cache:
            cached_data = self.cache[cache_key].copy()
            
            # Handle cache migration from old format
            if 'canonical_url' in cached_data:
                # Convert old canonical_url to canonical_path
                canonical_url = cached_data.pop('canonical_url')
                if canonical_url:
                    parsed = urlparse(canonical_url)
                    cached_data['canonical_path'] = parsed.path
                else:
                    cached_data['canonical_path'] = f"/ja/items/{item_id}"
            
            # Add missing fields with defaults
            if 'page_updated_at' not in cached_data:
                cached_data['page_updated_at'] = cached_data.get('updated_at')
            if 'related_item_ids' not in cached_data:
                cached_data['related_item_ids'] = []
            
            # Remove obsolete fields
            cached_data.pop('updated_at', None)
            
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
        
        # Scrape the item using enhanced retry logic
        url = f"https://booth.pm/ja/items/{item_id}"
        
        try:
            logger.debug(f"Scraping item {item_id}: {url}")
            response = self._get_with_retry(url)
            
            if response.status_code == 200:
                metadata = self._extract_metadata(response.text, item_id, response.url)
                logger.info(f"Successfully scraped item {item_id}: {metadata.name}")
                
                # Cache successful result
                self.cache[cache_key] = asdict(metadata)
                self._save_cache()
                
                return metadata
            
            elif response.status_code == 404:
                error_msg = f"Item {item_id} not found (404)"
                logger.warning(error_msg)
                
                # Cache 404 errors to avoid repeated requests (permanent error)
                error_metadata = ItemMetadata(item_id=item_id, error=error_msg)
                self.cache[cache_key] = asdict(error_metadata)
                self._save_cache()
                
                return error_metadata
            
            else:
                error_msg = f"HTTP {response.status_code} for item {item_id}"
                logger.warning(error_msg)
                
                # Cache other HTTP errors with shortened retry time for temporary failures
                error_metadata = ItemMetadata(item_id=item_id, error=error_msg)
                self.cache[cache_key] = asdict(error_metadata)
                self._save_cache()
                
                return error_metadata
        
        except requests.exceptions.Timeout:
            error_msg = f"Timeout scraping item {item_id} after retries"
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