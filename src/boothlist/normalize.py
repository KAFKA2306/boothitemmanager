"""Data normalization with avatar dictionary and schema transformation."""

import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict
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
        
        # Improve type inference from name and description if type is 'other'
        if item_type == 'other':
            item_type = self._infer_type_from_text(name, metadata.description_excerpt)
        
        # Normalize files
        file_list = metadata.files if metadata.files else raw_item.files
        normalized_files = self.normalize_files(file_list)
        
        # Extract avatar targets
        targets = self.extract_avatar_targets(
            name=name,
            files=file_list,
            description=metadata.description_excerpt
        )
        
        # Auto-assign avatar targets to avatar-type items
        if item_type == 'avatar' and not targets:
            targets = self._auto_assign_avatar_targets(name, metadata.description_excerpt)
        
        # Create normalized item
        item = Item(
            item_id=raw_item.item_id,
            type=item_type,
            name=name,
            shop_name=metadata.shop_name,
            creator_id=metadata.creator_id,
            image_url=metadata.image_url,
            url=self._build_canonical_url(metadata.canonical_path) or raw_item.url,
            current_price=metadata.current_price,
            description_excerpt=metadata.description_excerpt,
            files=normalized_files,
            targets=targets,
            tags=[],  # TODO: Implement tag extraction
            updated_at=metadata.page_updated_at or metadata.scraped_at or datetime.now().isoformat()
        )
        
        # Generate variants if this appears to be a set product
        item.variants = self.generate_variants(item)
        
        return item
    
    def _infer_type_from_text(self, name: str, description: Optional[str]) -> str:
        """Infer item type from name and description text."""
        combined_text = ((name or '') + ' ' + (description or '')).lower()
        
        # Type keywords mapping (Japanese and English)
        type_keywords = {
            'avatar': ['avatar', 'アバター', '3dアバター', '3d avatar'],
            'costume': ['costume', '衣装', 'clothing', 'dress', 'outfit', 'コスチューム', 'ワンピース', '服装'],
            'accessory': ['accessory', 'アクセサリ', 'アクセサリー', 'hair', 'ヘア', '髪型', 'hat', '帽子', 'glasses', 'メガネ'],
            'texture': ['texture', 'テクスチャ', '素材', 'material', 'skin', 'スキン', 'nail', 'ネイル'],
            'gimmick': ['gimmick', 'ギミック', 'script', 'スクリプト', 'animation', 'アニメーション'],
            'world': ['world', 'ワールド', 'scene', 'シーン', '背景', 'background'],
            'tool': ['tool', 'ツール', 'unity', 'blender', 'editor', 'エディタ'],
            'scenario': ['scenario', 'シナリオ', 'story', 'ストーリー', '物語']
        }
        
        # Check for keywords in text
        for item_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in combined_text:
                    logger.debug(f"Inferred type '{item_type}' from keyword '{keyword}' in text")
                    return item_type
        
        # Check filename patterns for additional clues
        for item_type, keywords in type_keywords.items():
            for keyword in keywords:
                if any(keyword in filename.lower() for filename in (name or '').split()):
                    return item_type
        
        return 'other'
    
    def _auto_assign_avatar_targets(self, name: str, description: Optional[str]) -> List[AvatarRef]:
        """Auto-assign avatar targets for avatar-type items."""
        avatar_refs = []
        combined_text = (name or '') + ' ' + (description or '')
        
        # Try to identify the avatar from name/description
        for avatar_code, avatar in self.avatar_dict.avatars.items():
            # Check main name and aliases
            if avatar_code.lower() in combined_text.lower():
                ref = self.avatar_dict.get_avatar_ref(avatar_code)
                if ref and ref not in avatar_refs:
                    avatar_refs.append(ref)
                    break
            
            if avatar.name_ja in combined_text:
                ref = self.avatar_dict.get_avatar_ref(avatar_code)
                if ref and ref not in avatar_refs:
                    avatar_refs.append(ref)
                    break
            
            for alias in avatar.aliases:
                if alias.lower() in combined_text.lower():
                    ref = self.avatar_dict.get_avatar_ref(avatar_code)
                    if ref and ref not in avatar_refs:
                        avatar_refs.append(ref)
                        break
        
        return avatar_refs
    
    def generate_variants(self, item: Item) -> List[Variant]:
        """Generate variants from filename patterns and text analysis (depth 1)."""
        variants = []
        
        # Only generate variants for items that could be sets
        if not self._is_potential_set_item(item):
            return variants
        
        # Extract avatar-specific variants from files
        avatar_variants = self._extract_avatar_variants_from_files(item)
        variants.extend(avatar_variants)
        
        # Extract variants from text patterns
        text_variants = self._extract_variants_from_text(item)
        variants.extend(text_variants)
        
        # Deduplicate variants
        variants = self._deduplicate_variants(variants)
        
        logger.debug(f"Generated {len(variants)} variants for item {item.item_id}")
        return variants
    
    def _is_potential_set_item(self, item: Item) -> bool:
        """Determine if an item could be a set product."""
        # Check for set indicators in name
        set_keywords = ['set', 'セット', 'pack', 'パック', 'bundle', 'バンドル', 'collection', 'コレクション']
        name_lower = (item.name or '').lower()
        
        for keyword in set_keywords:
            if keyword in name_lower:
                return True
        
        # Check if multiple avatars are targeted
        if len(item.targets) > 1:
            return True
        
        # Check if files contain multiple avatar prefixes
        avatar_prefixes = set()
        for file_asset in item.files:
            for avatar_code in self.avatar_dict.avatars.keys():
                if file_asset.filename.lower().startswith(avatar_code.lower() + '_'):
                    avatar_prefixes.add(avatar_code)
        
        if len(avatar_prefixes) > 1:
            return True
        
        return False
    
    def _extract_avatar_variants_from_files(self, item: Item) -> List[Variant]:
        """Extract avatar-specific variants from filename patterns."""
        variants = []
        avatar_files = defaultdict(list)
        
        # Group files by avatar prefix
        for file_asset in item.files:
            filename = file_asset.filename.lower()
            for avatar_code in self.avatar_dict.avatars.keys():
                avatar_lower = avatar_code.lower()
                if filename.startswith(avatar_lower + '_'):
                    avatar_files[avatar_code].append(file_asset)
                    break
        
        # Create variants for each avatar with files
        for avatar_code, files in avatar_files.items():
            if len(files) > 0:
                avatar_ref = self.avatar_dict.get_avatar_ref(avatar_code)
                if avatar_ref:
                    variant_name = f"{item.name} for {avatar_ref.name}"
                    variant_id = self.generate_variant_id(item.item_id, avatar_code, variant_name)
                    
                    variant = Variant(
                        subitem_id=variant_id,
                        parent_item_id=item.item_id,
                        variant_name=variant_name,
                        targets=[avatar_ref],
                        files=files,
                        notes=f"Files: {', '.join([f.filename for f in files[:3]])}" + ('...' if len(files) > 3 else '')
                    )
                    variants.append(variant)
        
        return variants
    
    def _extract_variants_from_text(self, item: Item) -> List[Variant]:
        """Extract variants from text patterns in description."""
        variants = []
        
        if not item.description_excerpt:
            return variants
        
        # Look for explicit avatar listings
        patterns = [
            r'対応[アバター]*[：:]\s*([^。\n]+)',
            r'Compatible\s+with[：:]?\s*([^.\n]+)',
            r'for\s+([^.\n]*(?:Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki)[^.\n]*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, item.description_excerpt, re.IGNORECASE)
            for match in matches:
                # Extract individual avatar names from the match
                mentioned_avatars = []
                for avatar_code in self.avatar_dict.avatars.keys():
                    avatar = self.avatar_dict.avatars[avatar_code]
                    if (avatar_code.lower() in match.lower() or 
                        avatar.name_ja in match or
                        any(alias.lower() in match.lower() for alias in avatar.aliases)):
                        mentioned_avatars.append(avatar_code)
                
                # Create variants for mentioned avatars
                for avatar_code in mentioned_avatars:
                    avatar_ref = self.avatar_dict.get_avatar_ref(avatar_code)
                    if avatar_ref:
                        variant_name = f"{item.name} for {avatar_ref.name}"
                        variant_id = self.generate_variant_id(item.item_id, avatar_code, variant_name)
                        
                        variant = Variant(
                            subitem_id=variant_id,
                            parent_item_id=item.item_id,
                            variant_name=variant_name,
                            targets=[avatar_ref],
                            files=[],  # No specific files for text-based variants
                            notes="Extracted from description text"
                        )
                        variants.append(variant)
        
        return variants
    
    def _deduplicate_variants(self, variants: List[Variant]) -> List[Variant]:
        """Remove duplicate variants based on subitem_id."""
        seen_ids = set()
        unique_variants = []
        
        for variant in variants:
            if variant.subitem_id not in seen_ids:
                seen_ids.add(variant.subitem_id)
                unique_variants.append(variant)
        
        return unique_variants
    
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
    
    def _build_canonical_url(self, canonical_path: Optional[str]) -> Optional[str]:
        """Build full URL from canonical path."""
        if not canonical_path:
            return None
        return f"https://booth.pm{canonical_path}"


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