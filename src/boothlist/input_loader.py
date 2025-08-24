"""Input loader for BOOTH purchase data from various formats (YAML, CSV, text)."""

import re
import yaml
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RawItem:
    """Raw item data before normalization."""
    item_id: int
    name: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    variation: Optional[str] = None
    files: List[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    wish_price: Optional[int] = None
    
    def __post_init__(self):
        if self.files is None:
            self.files = []


class InputLoader:
    """Loads and normalizes purchase data from various input formats."""
    
    BOOTH_URL_PATTERNS = [
        r'https?://booth\.pm/(?:ja/|en/)?items/(\d+)',
        r'https?://[\w-]+\.booth\.pm/items/(\d+)',
        r'booth\.pm/(?:ja/|en/)?items/(\d+)',
        r'items/(\d+)(?:[/?#]|$)',
        r'booth\.pm/items/(\d+)',
        r'booth\.pm/(\d+)',  # Short format
        r'/items/(\d+)',
        r'item[_-]?id[=:](\d+)',  # Query parameter format
        r'(?:item|product)[_-]?(\d+)',  # Generic item format
        r'(\d{7,8})(?:[^\d]|$)'  # Standalone 7-8 digit numbers (BOOTH item IDs)
    ]
    
    def __init__(self):
        self.url_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.BOOTH_URL_PATTERNS]
    
    def extract_item_id(self, text: str) -> Optional[int]:
        """Extract BOOTH item ID from URL or text."""
        if not text:
            return None
            
        for regex in self.url_regex:
            match = regex.search(text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None
    
    def load_yaml(self, file_path: Union[str, Path]) -> List[RawItem]:
        """Load items from YAML file (booth3.yaml format)."""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"YAML file not found: {file_path}")
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            items = []
            booth_purchases = data.get('booth_purchases', [])
            
            for item_data in booth_purchases:
                item_id = item_data.get('id')
                if not item_id:
                    logger.warning(f"Skipping item without ID: {item_data}")
                    continue
                
                raw_item = RawItem(
                    item_id=item_id,
                    name=item_data.get('name'),
                    author=item_data.get('author'),
                    category=item_data.get('category'),
                    variation=item_data.get('variation'),
                    files=item_data.get('files', []),
                    notes=item_data.get('notes'),
                    wish_price=item_data.get('wish_price')
                )
                raw_item.url = f"https://booth.pm/ja/items/{item_id}"
                items.append(raw_item)
                
            logger.info(f"Loaded {len(items)} items from YAML: {file_path}")
            return items
            
        except Exception as e:
            logger.error(f"Error loading YAML file {file_path}: {e}")
            return []
    
    def load_markdown(self, file_path: Union[str, Path]) -> List[RawItem]:
        """Load items from markdown file (booth.md format)."""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"Markdown file not found: {file_path}")
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            items = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                item_id = self.extract_item_id(line)
                if item_id:
                    # Try to extract title from markdown link format [title](url)
                    md_link_match = re.search(r'\[([^\]]+)\]\([^)]+\)', line)
                    name = md_link_match.group(1) if md_link_match else None
                    
                    raw_item = RawItem(
                        item_id=item_id,
                        name=name,
                        url=f"https://booth.pm/ja/items/{item_id}"
                    )
                    items.append(raw_item)
            
            # Remove duplicates based on item_id
            seen_ids = set()
            unique_items = []
            for item in items:
                if item.item_id not in seen_ids:
                    seen_ids.add(item.item_id)
                    unique_items.append(item)
            
            logger.info(f"Loaded {len(unique_items)} unique items from markdown: {file_path}")
            return unique_items
            
        except Exception as e:
            logger.error(f"Error loading markdown file {file_path}: {e}")
            return []
    
    def load_csv(self, file_path: Union[str, Path]) -> List[RawItem]:
        """Load items from CSV file."""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.warning(f"CSV file not found: {file_path}")
            return []
            
        try:
            items = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Try to extract item_id from various columns
                    item_id = None
                    for col in ['id', 'item_id', 'url', 'link']:
                        if col in row and row[col]:
                            extracted_id = self.extract_item_id(str(row[col]))
                            if extracted_id:
                                item_id = extracted_id
                                break
                    
                    if not item_id:
                        logger.warning(f"Skipping CSV row without valid item ID: {row}")
                        continue
                    
                    raw_item = RawItem(
                        item_id=item_id,
                        name=row.get('name') or row.get('title'),
                        author=row.get('author') or row.get('creator') or row.get('shop'),
                        category=row.get('category') or row.get('type'),
                        variation=row.get('variation') or row.get('variant'),
                        notes=row.get('notes') or row.get('memo'),
                        wish_price=self._parse_price(row.get('price') or row.get('wish_price')),
                        url=f"https://booth.pm/ja/items/{item_id}"
                    )
                    items.append(raw_item)
            
            logger.info(f"Loaded {len(items)} items from CSV: {file_path}")
            return items
            
        except Exception as e:
            logger.error(f"Error loading CSV file {file_path}: {e}")
            return []
    
    def _parse_price(self, price_str: Optional[str]) -> Optional[int]:
        """Parse price string to integer."""
        if not price_str:
            return None
        
        try:
            # Remove currency symbols and separators
            price_clean = re.sub(r'[¥,\s]', '', str(price_str))
            return int(price_clean) if price_clean.isdigit() else None
        except (ValueError, AttributeError):
            return None
    
    def load_from_directory(self, input_dir: Union[str, Path]) -> List[RawItem]:
        """Load all supported files from input directory."""
        input_dir = Path(input_dir)
        if not input_dir.exists():
            logger.warning(f"Input directory not found: {input_dir}")
            return []
        
        all_items = []
        
        # Load YAML files
        for yaml_file in input_dir.glob('*.yaml'):
            items = self.load_yaml(yaml_file)
            all_items.extend(items)
        
        for yml_file in input_dir.glob('*.yml'):
            items = self.load_yaml(yml_file)
            all_items.extend(items)
        
        # Load markdown files
        for md_file in input_dir.glob('*.md'):
            items = self.load_markdown(md_file)
            all_items.extend(items)
        
        # Load CSV files
        for csv_file in input_dir.glob('*.csv'):
            items = self.load_csv(csv_file)
            all_items.extend(items)
        
        # Remove duplicates based on item_id
        seen_ids = set()
        unique_items = []
        for item in all_items:
            if item.item_id not in seen_ids:
                seen_ids.add(item.item_id)
                unique_items.append(item)
            else:
                logger.debug(f"Duplicate item_id {item.item_id} skipped")
        
        logger.info(f"Loaded {len(unique_items)} unique items from directory: {input_dir}")
        return unique_items
    
    def validate_items(self, items: List[RawItem]) -> List[RawItem]:
        """Validate and filter items with enhanced checks."""
        valid_items = []
        validation_errors = []
        
        for item in items:
            # Check item_id validity
            if not item.item_id:
                validation_errors.append(f"Missing item_id for item: {item.name or 'Unknown'}")
                continue
            
            if not isinstance(item.item_id, int) or item.item_id <= 0:
                validation_errors.append(f"Invalid item_id: {item.item_id}")
                continue
            
            # BOOTH item ID range validation
            if not (1000000 <= item.item_id <= 99999999):
                validation_errors.append(f"Item_id {item.item_id} outside valid BOOTH range (1M-99M)")
                continue
            
            # Construct URL if missing
            if not item.url:
                item.url = f"https://booth.pm/ja/items/{item.item_id}"
            
            # Basic validation passed
            valid_items.append(item)
        
        # Log validation summary
        if validation_errors:
            logger.warning(f"Validation errors ({len(validation_errors)}):")
            for error in validation_errors[:5]:  # Show first 5 errors
                logger.warning(f"  {error}")
            if len(validation_errors) > 5:
                logger.warning(f"  ... and {len(validation_errors) - 5} more errors")
        
        logger.info(f"Validated {len(valid_items)} items out of {len(items)}")
        return valid_items
    
    def get_extraction_stats(self, items: List[RawItem]) -> Dict[str, Any]:
        """Get statistics about ID extraction success."""
        total_items = len(items)
        valid_ids = sum(1 for item in items if item.item_id and 1000000 <= item.item_id <= 99999999)
        
        return {
            'total_items': total_items,
            'valid_ids': valid_ids,
            'extraction_rate': (valid_ids / total_items) * 100 if total_items > 0 else 0
        }


def main():
    """Test the input loader with sample data."""
    logging.basicConfig(level=logging.INFO)
    
    loader = InputLoader()
    
    # Test with booth3.yaml
    items = loader.load_from_directory('/home/kafka/projects/boothlist/input')
    
    print(f"Loaded {len(items)} items:")
    for item in items[:5]:  # Show first 5 items
        print(f"  {item.item_id}: {item.name} by {item.author} ({item.category})")


if __name__ == '__main__':
    main()