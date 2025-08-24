"""Data normalization with avatar dictionary and schema transformation."""

import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class AvatarRef:
    """Reference to an avatar with code and display name."""
    code: str
    name: str


@dataclass
class FileAsset:
    """File asset information."""
    filename: str
    version: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None


@dataclass
class Item:
    """Normalized item data model."""
    item_id: int
    type: str  # "avatar" | "costume" | "accessory" | "tool" | "gimmick" | "world" | "texture" | "scenario" | "bundle" | "other"
    name: str
    shop_name: Optional[str] = None
    creator_id: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    current_price: Optional[int] = None
    description_excerpt: Optional[str] = None
    files: List[FileAsset] = None
    targets: List[AvatarRef] = None
    tags: List[str] = None
    updated_at: Optional[str] = None
    variants: List['Variant'] = None
    
    def __post_init__(self):
        if self.files is None:
            self.files = []
        if self.targets is None:
            self.targets = []
        if self.tags is None:
            self.tags = []
        if self.variants is None:
            self.variants = []


@dataclass
class Variant:
    """Virtual subitem/variant within a set product."""
    subitem_id: str  # Format: {parent_item_id}#variant:{avatar_code}:{slug}
    parent_item_id: int
    variant_name: str
    targets: List[AvatarRef] = None
    files: List[FileAsset] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.targets is None:
            self.targets = []
        if self.files is None:
            self.files = []


@dataclass
class Avatar:
    """Avatar definition with aliases."""
    code: str  # Normalized key
    name_ja: str  # Japanese name
    aliases: List[str] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class AvatarDictionary:
    """Avatar dictionary for normalizing avatar names and aliases."""
    
    def __init__(self):
        # Based on design.md specifications
        self.avatars = {
            'Selestia': Avatar(
                code='Selestia',
                name_ja='セレスティア',
                aliases=['セレスティア', 'selestia', 'SELESTIA', 'Celestia']
            ),
            'Kikyo': Avatar(
                code='Kikyo',
                name_ja='桔梗',
                aliases=['桔梗', 'kikyo', 'KIKYO', 'kikyou', 'Kikyou']
            ),
            'Kanae': Avatar(
                code='Kanae', 
                name_ja='かなえ',
                aliases=['かなえ', 'kanae', 'KANAE', 'カナエ']
            ),
            'Shinano': Avatar(
                code='Shinano',
                name_ja='しなの', 
                aliases=['しなの', 'shinano', 'SHINANO', 'シナノ']
            ),
            'Manuka': Avatar(
                code='Manuka',
                name_ja='マヌカ',
                aliases=['マヌカ', 'manuka', 'MANUKA']
            ),
            'Moe': Avatar(
                code='Moe',
                name_ja='萌',
                aliases=['萌', 'moe', 'MOE']
            ),
            'Rurune': Avatar(
                code='Rurune',
                name_ja='ルルネ',
                aliases=['ルルネ', 'rurune', 'RURUNE']
            ),
            'Hakka': Avatar(
                code='Hakka',
                name_ja='薄荷',
                aliases=['薄荷', 'hakka', 'HAKKA']
            ),
            'Mizuki': Avatar(
                code='Mizuki',
                name_ja='瑞希',
                aliases=['瑞希', 'mizuki', 'MIZUKI']
            )
        }
        
        # Build reverse lookup for aliases
        self.alias_to_code = {}
        for avatar in self.avatars.values():
            # Add the code itself
            self.alias_to_code[avatar.code] = avatar.code
            self.alias_to_code[avatar.code.lower()] = avatar.code
            
            # Add all aliases
            for alias in avatar.aliases:
                self.alias_to_code[alias] = avatar.code
                self.alias_to_code[alias.lower()] = avatar.code
    
    def normalize_avatar(self, avatar_text: str) -> Optional[str]:
        """Normalize avatar text to standard code."""
        if not avatar_text:
            return None
        
        # Direct lookup
        if avatar_text in self.alias_to_code:
            return self.alias_to_code[avatar_text]
        
        # Case-insensitive lookup
        if avatar_text.lower() in self.alias_to_code:
            return self.alias_to_code[avatar_text.lower()]
        
        return None
    
    def get_avatar(self, code: str) -> Optional[Avatar]:
        """Get avatar by code."""
        return self.avatars.get(code)
    
    def get_avatar_ref(self, code: str) -> Optional[AvatarRef]:
        """Get AvatarRef by code."""
        avatar = self.get_avatar(code)
        if avatar:
            return AvatarRef(code=avatar.code, name=avatar.name_ja)
        return None


class DataNormalizer:
    """Normalizes raw data to structured schema."""
    
    # Category mapping from input to normalized type
    CATEGORY_MAPPING = {
        '3D Avatar': 'avatar',
        '3D Clothing': 'costume',
        '3D Accessory': 'accessory',
        'Tool': 'tool',
        'Gimmick': 'gimmick',
        'World': 'world',
        'Texture': 'texture',
        'Scenario': 'scenario',
        'Bundle': 'bundle',
        # Japanese categories
        'アバター': 'avatar',
        '衣装': 'costume',
        'アクセサリ': 'accessory',
        'アクセサリー': 'accessory',
        'ツール': 'tool',
        'ギミック': 'gimmick',
        'ワールド': 'world',
        'テクスチャ': 'texture',
        '素材': 'texture',
        'シナリオ': 'scenario',
        'セット': 'bundle',
    }
    
    def __init__(self):
        self.avatar_dict = AvatarDictionary()
    
    def normalize_type(self, category: Optional[str]) -> str:
        """Normalize category to standard type."""
        if not category:
            return 'other'
        
        # Direct mapping
        if category in self.CATEGORY_MAPPING:
            return self.CATEGORY_MAPPING[category]
        
        # Case-insensitive search
        for key, value in self.CATEGORY_MAPPING.items():
            if category.lower() == key.lower():
                return value
        
        # Partial matching for common terms
        category_lower = category.lower()
        if 'avatar' in category_lower or 'アバター' in category_lower:
            return 'avatar'
        elif 'costume' in category_lower or '衣装' in category_lower:
            return 'costume'
        elif 'accessor' in category_lower or 'アクセサリ' in category_lower:
            return 'accessory'
        elif 'tool' in category_lower or 'ツール' in category_lower:
            return 'tool'
        elif 'world' in category_lower or 'ワールド' in category_lower:
            return 'world'
        
        logger.debug(f"Unknown category '{category}', using 'other'")
        return 'other'
    
    def normalize_files(self, file_list: List[str]) -> List[FileAsset]:
        """Convert file list to FileAsset objects."""
        if not file_list:
            return []
        
        assets = []
        for filename in file_list:
            if not filename:
                continue
                
            # Try to extract version from filename
            version = self._extract_version(filename)
            
            asset = FileAsset(filename=filename, version=version)
            assets.append(asset)
        
        return assets
    
    def _extract_version(self, filename: str) -> Optional[str]:
        """Extract version information from filename."""
        # Common version patterns
        version_patterns = [
            r'[vV](\d+(?:\.\d+)*)',
            r'Ver(\d+(?:\.\d+)*)',
            r'ver(\d+(?:\.\d+)*)',
            r'V(\d+(?:\.\d+)*)',
            r'_(\d+\.\d+)(?:\.|_|$)'
        ]
        
        for pattern in version_patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        
        return None
    
    def extract_avatar_targets(self, name: str, files: List[str], description: Optional[str] = None) -> List[AvatarRef]:
        """Extract avatar targets from name, files, and description."""
        avatar_codes = set()
        
        # Check filename patterns first (highest confidence)
        for filename in files:
            for avatar_code in self.avatar_dict.avatars.keys():
                # Check prefix patterns: Kikyo_, Selestia_
                if filename.startswith(f"{avatar_code}_"):
                    avatar_codes.add(avatar_code)
                    continue
                
                # Check suffix patterns: _Kikyo, _Selestia  
                if f"_{avatar_code}" in filename:
                    avatar_codes.add(avatar_code)
                    continue
                
                # Check case-insensitive patterns
                filename_lower = filename.lower()
                avatar_lower = avatar_code.lower()
                if filename_lower.startswith(f"{avatar_lower}_") or f"_{avatar_lower}" in filename_lower:
                    avatar_codes.add(avatar_code)
        
        # Check name and description for explicit mentions
        combined_text = (name or '') + ' ' + (description or '')
        
        # Japanese patterns
        japanese_patterns = [
            r'対応アバター[：:]\s*([^。\n]+)',
            r'対応[：:]?\s*([^。\n]*(?:セレスティア|桔梗|かなえ|しなの|マヌカ|萌|ルルネ|薄荷|瑞希)[^。\n]*)',
        ]
        
        for pattern in japanese_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                for avatar_code in self.avatar_dict.avatars.keys():
                    avatar = self.avatar_dict.avatars[avatar_code]
                    if avatar.name_ja in match:
                        avatar_codes.add(avatar_code)
        
        # English patterns  
        english_patterns = [
            r'for\s+(Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki)',
            r'(Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki)\s*用',
        ]
        
        for pattern in english_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                normalized = self.avatar_dict.normalize_avatar(match)
                if normalized:
                    avatar_codes.add(normalized)
        
        # Convert to AvatarRef objects
        avatar_refs = []
        for code in avatar_codes:
            ref = self.avatar_dict.get_avatar_ref(code)
            if ref:
                avatar_refs.append(ref)
        
        return avatar_refs
    
    def normalize_item(self, raw_item, metadata) -> Item:
        """Normalize raw item and metadata to Item object."""
        # Use metadata name if available, fallback to raw item name
        name = metadata.name or raw_item.name or f"Item {raw_item.item_id}"
        
        # Normalize type
        item_type = self.normalize_type(raw_item.category)
        
        # Normalize files
        file_list = metadata.files if metadata.files else raw_item.files
        normalized_files = self.normalize_files(file_list)
        
        # Extract avatar targets
        targets = self.extract_avatar_targets(
            name=name,
            files=file_list,
            description=metadata.description_excerpt
        )
        
        # Create normalized item
        item = Item(
            item_id=raw_item.item_id,
            type=item_type,
            name=name,
            shop_name=metadata.shop_name,
            creator_id=metadata.creator_id,
            image_url=metadata.image_url,
            url=metadata.canonical_url or raw_item.url,
            current_price=metadata.current_price,
            description_excerpt=metadata.description_excerpt,
            files=normalized_files,
            targets=targets,
            tags=[],  # TODO: Implement tag extraction
            updated_at=metadata.updated_at or datetime.now().isoformat()
        )
        
        return item
    
    def create_slug(self, text: str) -> str:
        """Create URL-safe slug from text."""
        if not text:
            return 'unknown'
        
        # Convert to lowercase
        slug = text.lower()
        
        # Replace spaces and special characters with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_-]+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # Limit length
        if len(slug) > 50:
            slug = slug[:50].rstrip('-')
        
        return slug or 'unknown'
    
    def generate_variant_id(self, parent_item_id: int, avatar_code: str, variant_name: str) -> str:
        """Generate virtual ID for variant."""
        slug = self.create_slug(variant_name)
        return f"{parent_item_id}#variant:{avatar_code}:{slug}"


def main():
    """Test the normalizer with sample data."""
    logging.basicConfig(level=logging.INFO)
    
    normalizer = DataNormalizer()
    
    # Test avatar extraction
    test_files = [
        "Kikyo_Marshmallow_Ver1.00.zip",
        "Selestia_Marshmallow_Ver1.00.zip",
        "Kanae_SummerOutfit_v2.1.zip"
    ]
    
    targets = normalizer.extract_avatar_targets(
        name="Marshmallow Full Set",
        files=test_files,
        description="対応アバター: セレスティア、桔梗、かなえ"
    )
    
    print("Extracted avatar targets:")
    for target in targets:
        print(f"  {target.code}: {target.name}")
    
    # Test type normalization
    test_categories = ['3D Avatar', '3D Clothing', 'Tool', '衣装', 'アバター']
    print("\nType normalization:")
    for category in test_categories:
        normalized = normalizer.normalize_type(category)
        print(f"  {category} -> {normalized}")


if __name__ == '__main__':
    main()