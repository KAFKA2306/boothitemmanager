"""Data normalization with avatar dictionary and schema transformation."""

import re
import yaml
import unicodedata
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict
import logging
from pathlib import Path

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
    """Avatar dictionary for normalizing avatar names and aliases using aliases.yml."""
    
    def __init__(self, aliases_file: str = 'aliases.yml'):
        self.aliases_file = aliases_file
        self.avatars = {}
        self.alias_to_code = {}
        self.type_aliases = {}
        self.options = {}
        self._load_aliases()
    
    def _load_aliases(self):
        """Load avatar and type aliases from YAML file."""
        aliases_path = Path(self.aliases_file)
        
        # Fallback to hardcoded if file doesn't exist
        if not aliases_path.exists():
            logger.warning(f"Aliases file {self.aliases_file} not found, using hardcoded avatars")
            self._load_hardcoded_avatars()
            return
        
        try:
            with open(aliases_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self.options = data.get('options', {})
            
            # Load avatars
            avatars_data = data.get('avatars', {})
            for code, avatar_data in avatars_data.items():
                avatar = Avatar(
                    code=code,
                    name_ja=avatar_data.get('name_ja', code),
                    aliases=avatar_data.get('aliases', [])
                )
                self.avatars[code] = avatar
            
            # Load type aliases
            types_data = data.get('types', {})
            for type_name, type_data in types_data.items():
                self.type_aliases[type_name] = type_data.get('aliases', [])
            
            # Build reverse lookup
            self._build_alias_lookup()
            
            logger.info(f"Loaded {len(self.avatars)} avatars and {len(self.type_aliases)} type categories from {self.aliases_file}")
            
        except Exception as e:
            logger.error(f"Error loading aliases file {self.aliases_file}: {e}")
            self._load_hardcoded_avatars()
    
    def _load_hardcoded_avatars(self):
        """Fallback hardcoded avatar definitions."""
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
            ),
            # New avatars
            'SUN': Avatar(
                code='SUN',
                name_ja='SUN',
                aliases=['SUN', 'Sun', 'サン']
            ),
            'INABA': Avatar(
                code='INABA',
                name_ja='INABA',
                aliases=['INABA', 'Inaba', 'いなば', 'イナバ']
            ),
            'Shiina': Avatar(
                code='Shiina',
                name_ja='椎名',
                aliases=['椎名', 'Shiina', 'SHIINA', 'しいな', 'シイナ']
            ),
            'KitsuneAme': Avatar(
                code='KitsuneAme',
                name_ja='狐雨',
                aliases=['狐雨', 'kitsuneame', 'KITSUNEAME', 'キツネアメ', 'きつねあめ']
            ),
            'NekoMaid': Avatar(
                code='NekoMaid',
                name_ja='猫メイド',
                aliases=['猫メイド', 'ネコメイド', 'nekomaid', 'NekoMaid', 'neko maid', 'ネコ メイド']
            )
        }
        self._build_alias_lookup()
    
    def _build_alias_lookup(self):
        """Build reverse lookup for aliases with text normalization."""
        self.alias_to_code = {}
        
        for avatar in self.avatars.values():
            # Add the code itself
            normalized_code = self._normalize_text(avatar.code)
            self.alias_to_code[avatar.code] = avatar.code
            self.alias_to_code[normalized_code] = avatar.code
            
            # Add all aliases
            for alias in avatar.aliases:
                normalized_alias = self._normalize_text(alias)
                self.alias_to_code[alias] = avatar.code
                self.alias_to_code[normalized_alias] = avatar.code
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text according to options in aliases.yml."""
        if not text:
            return text
        
        # Apply Unicode normalization
        if self.options.get('unicode_normalization') == 'NFKC':
            text = unicodedata.normalize('NFKC', text)
        
        # Case normalization
        if self.options.get('case_insensitive', True):
            text = text.lower()
        
        # Trim whitespace
        if self.options.get('trim_whitespace', True):
            text = text.strip()
        
        # Collapse inner spaces
        if self.options.get('collapse_inner_spaces', True):
            text = re.sub(r'\s+', ' ', text)
        
        # Strip symbols
        strip_symbols = self.options.get('strip_symbols', [])
        for symbol in strip_symbols:
            text = text.replace(symbol, '')
        
        return text
    
    def normalize_avatar(self, avatar_text: str) -> Optional[str]:
        """Normalize avatar text to standard code using enhanced matching."""
        if not avatar_text:
            return None
        
        # Direct lookup
        if avatar_text in self.alias_to_code:
            return self.alias_to_code[avatar_text]
        
        # Normalized lookup
        normalized_text = self._normalize_text(avatar_text)
        if normalized_text in self.alias_to_code:
            return self.alias_to_code[normalized_text]
        
        # Fallback: try to find partial matches for Japanese names in brackets
        # Handle patterns like "「SUN」" or "【椎名】" or "(Shiina)"
        bracket_pattern = r'[「【\(]([^」】\)]+)[」】\)]'
        match = re.search(bracket_pattern, avatar_text)
        if match:
            bracket_content = self._normalize_text(match.group(1))
            if bracket_content in self.alias_to_code:
                return self.alias_to_code[bracket_content]
        
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
    
    # Hardcoded category mapping (fallback if aliases.yml is not available)
    CATEGORY_MAPPING = {
        '3D Avatar': 'avatar',
        '3D Clothing': 'costume', 
        '3D Accessory': 'accessory',
        'Tool': 'tool',
        'Gimmick': 'gimmick',
        'gimick': 'gimmick',  # Common typo
        'World': 'world',
        'Texture': 'texture',
        'texture': 'texture',  # Case variation
        'TEXTURE': 'texture',
        'Scenario': 'scenario',
        'Bundle': 'bundle',
        'Goods': 'other',  # Fix goods classification
        'GOODS': 'other',
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
        'グッズ': 'other',
    }
    
    def __init__(self):
        self.avatar_dict = AvatarDictionary()
    
    def normalize_type(self, category: Optional[str]) -> str:
        """Normalize category to standard type using aliases.yml or fallback mapping."""
        if not category:
            return 'other'
        
        # First try aliases from YAML file
        if self.avatar_dict.type_aliases:
            normalized_category = self.avatar_dict._normalize_text(category)
            
            for type_name, aliases in self.avatar_dict.type_aliases.items():
                # Check direct alias match
                if category in aliases:
                    return type_name
                
                # Check normalized alias match
                normalized_aliases = [self.avatar_dict._normalize_text(alias) for alias in aliases]
                if normalized_category in normalized_aliases:
                    return type_name
        
        # Fallback to hardcoded mapping
        if category in self.CATEGORY_MAPPING:
            return self.CATEGORY_MAPPING[category]
        
        # Case-insensitive search in hardcoded mapping
        for key, value in self.CATEGORY_MAPPING.items():
            if category.lower() == key.lower():
                return value
        
        # Partial matching for common terms (fallback)
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
        """Extract avatar targets from name, files, and description with enhanced matching."""
        avatar_codes = set()
        
        # Check filename patterns first (highest confidence)
        for filename in files:
            for avatar_code in self.avatar_dict.avatars.keys():
                avatar_lower = avatar_code.lower()
                filename_lower = filename.lower()
                
                # Check prefix patterns: Kikyo_, Selestia_, SUN_
                if filename_lower.startswith(f"{avatar_lower}_"):
                    avatar_codes.add(avatar_code)
                    logger.debug(f"Found avatar {avatar_code} from filename prefix: {filename}")
                    continue
                
                # Check suffix patterns: _Kikyo, _Selestia, _SUN
                if f"_{avatar_lower}" in filename_lower:
                    avatar_codes.add(avatar_code)
                    logger.debug(f"Found avatar {avatar_code} from filename suffix: {filename}")
                    continue
                    
                # Check version patterns: SUN_v1.1.3, 01_INABA_ver4.0.1
                version_patterns = [
                    rf'{re.escape(avatar_lower)}[_\s]*v\d',
                    rf'\d+_{re.escape(avatar_lower)}_ver',
                    rf'{re.escape(avatar_lower)}ver',
                ]
                
                for pattern in version_patterns:
                    if re.search(pattern, filename_lower):
                        avatar_codes.add(avatar_code)
                        logger.debug(f"Found avatar {avatar_code} from version pattern: {filename}")
                        break
                        
                # Check Japanese name in filename
                avatar = self.avatar_dict.avatars[avatar_code]
                if avatar.name_ja and avatar.name_ja in filename:
                    avatar_codes.add(avatar_code)
                    logger.debug(f"Found avatar {avatar_code} from Japanese name in filename: {filename}")
        
        # Check name and description for explicit mentions
        combined_text = (name or '') + ' ' + (description or '')
        
        # Enhanced Japanese patterns including new avatars
        japanese_patterns = [
            r'対応アバター[：:]\s*([^。\n]+)',
            r'対応[：:]?\s*([^。\n]*(?:セレスティア|桔梗|かなえ|しなの|マヌカ|萌|ルルネ|薄荷|瑞希|SUN|INABA|椎名|狐雨|猫メイド)[^。\n]*)',
            # Bracket patterns for avatar names
            r'「([^」]+)」',
            r'【([^】]+)】',
        ]
        
        for pattern in japanese_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                # Try to match each avatar in the text
                for avatar_code in self.avatar_dict.avatars.keys():
                    avatar = self.avatar_dict.avatars[avatar_code]
                    
                    # Check Japanese name
                    if avatar.name_ja and avatar.name_ja in match:
                        avatar_codes.add(avatar_code)
                        logger.debug(f"Found avatar {avatar_code} from Japanese pattern: {match}")
                    
                    # Check code and aliases
                    normalized_code = self.avatar_dict.normalize_avatar(match.strip())
                    if normalized_code == avatar_code:
                        avatar_codes.add(avatar_code)
                        logger.debug(f"Found avatar {avatar_code} from normalized text: {match}")
        
        # Enhanced English patterns including new avatars
        english_patterns = [
            r'for\s+(Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki|SUN|INABA|Shiina|KitsuneAme|NekoMaid)',
            r'(Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki|SUN|INABA|Shiina|KitsuneAme|NekoMaid)\s*用',
            r'(Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki|SUN|INABA|Shiina|KitsuneAme|NekoMaid)\s+compatible',
        ]
        
        for pattern in english_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                normalized = self.avatar_dict.normalize_avatar(match)
                if normalized:
                    avatar_codes.add(normalized)
                    logger.debug(f"Found avatar {normalized} from English pattern: {match}")
        
        # Convert to AvatarRef objects
        avatar_refs = []
        for code in avatar_codes:
            ref = self.avatar_dict.get_avatar_ref(code)
            if ref:
                avatar_refs.append(ref)
        
        logger.debug(f"Extracted {len(avatar_refs)} avatar targets: {[ref.code for ref in avatar_refs]}")
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
        """Infer item type from name and description text with priority-based scoring."""
        combined_text = ((name or '') + ' ' + (description or '')).lower()
        
        # Priority-based type keywords (higher number = higher priority)
        # Priority order per aliases.md: gimmick > tool > world > texture > accessory > costume
        type_keywords = {
            'gimmick': {
                'priority': 10,
                'keywords': ['gimmick', 'gimick', 'ギミック', 'modularavatar', 'モジュラーアバター', 
                           'system', 'システム', '仕組み', '機能', '寝返り', 'ovr', 'アニメーション制御']
            },
            'tool': {
                'priority': 9,
                'keywords': ['tool', 'ツール', 'unity', 'editor', 'エディタ', 'インストーラ', 
                           'installer', 'script', 'スクリプト', 'unitypackage', 'ユニティ']
            },
            'world': {
                'priority': 8, 
                'keywords': ['world', 'ワールド', 'scene', 'シーン', '背景', 'background', 
                           'ステージ', 'マップ', 'ロケーション', '空間', 'カフェ', 'cafe', '会場']
            },
            'texture': {
                'priority': 7,
                'keywords': ['texture', 'テクスチャ', '素材', 'material', 'skin', 'スキン', 
                           'nail', 'ネイル', '肌', 'ボディ', 'ボディテクスチャ', '顔', 'フェイス',
                           'リップ', '唇', '眉', 'まゆ', '瞳', '目', '虹彩']
            },
            'accessory': {
                'priority': 6,
                'keywords': ['accessory', 'アクセサリ', 'アクセサリー', 'hair', 'ヘア', '髪型', 
                           'hat', '帽子', 'glasses', 'メガネ', 'ピアス', 'イヤリング', '靴', 'シューズ']
            },
            'costume': {
                'priority': 5,
                'keywords': ['costume', '衣装', 'clothing', 'dress', 'outfit', 'コスチューム', 
                           'ワンピース', '服装', 'ドレス', 'スカート', '水着', '浴衣', 'セーラー', 'メイド服']
            },
            'avatar': {
                'priority': 4,
                'keywords': ['avatar', 'アバター', '3dアバター', '3d avatar']
            },
            'scenario': {
                'priority': 3,
                'keywords': ['scenario', 'シナリオ', 'story', 'ストーリー', '物語', '台本', 'セリフ']
            },
            'bundle': {
                'priority': 2,
                'keywords': ['bundle', 'セット', 'セット商品', 'フルセット', 'full set', 
                           'パック', 'pack', 'コレクション', 'collection']
            },
            'other': {
                'priority': 1,
                'keywords': ['goods', 'グッズ', '物販', 'アクスタ', 'ステッカー']
            }
        }
        
        # Score each type based on keyword matches
        type_scores = {}
        
        for item_type, config in type_keywords.items():
            score = 0
            priority = config['priority']
            
            for keyword in config['keywords']:
                if keyword in combined_text:
                    # Base score from priority, bonus for exact matches
                    score += priority * 10
                    logger.debug(f"Found keyword '{keyword}' for type '{item_type}', score: {score}")
                    
            if score > 0:
                type_scores[item_type] = score
        
        # Return the highest scoring type
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])
            logger.debug(f"Inferred type '{best_type[0]}' with score {best_type[1]} from text analysis")
            return best_type[0]
        
        logger.debug(f"No keywords matched, using 'other' for text: {combined_text[:100]}...")
        return 'other'
    
    def _auto_assign_avatar_targets(self, name: str, description: Optional[str]) -> List[AvatarRef]:
        """Auto-assign avatar targets for avatar-type items with enhanced pattern matching."""
        avatar_refs = []
        combined_text = (name or '') + ' ' + (description or '')
        
        # Enhanced patterns for avatar detection
        patterns_to_try = [
            # Japanese brackets patterns
            r'「([^」]+)」',
            r'【([^】]+)】', 
            # Version patterns
            r'([A-Za-z][A-Za-z0-9]*)[\s_]*[vV]?\d',
            # Direct name patterns
            combined_text,
        ]
        
        for pattern in patterns_to_try:
            if pattern == combined_text:
                # Direct text search
                search_texts = [combined_text]
            else:
                # Regex pattern search
                matches = re.findall(pattern, combined_text)
                search_texts = matches if matches else []
            
            for search_text in search_texts:
                # Try to identify the avatar from each search text
                for avatar_code, avatar in self.avatar_dict.avatars.items():
                    # Check main code (case insensitive)
                    if avatar_code.lower() in search_text.lower():
                        ref = self.avatar_dict.get_avatar_ref(avatar_code)
                        if ref and ref not in avatar_refs:
                            avatar_refs.append(ref)
                            logger.debug(f"Auto-assigned avatar {avatar_code} from code match in: {search_text}")
                            continue
                    
                    # Check Japanese name
                    if avatar.name_ja in search_text:
                        ref = self.avatar_dict.get_avatar_ref(avatar_code)
                        if ref and ref not in avatar_refs:
                            avatar_refs.append(ref)
                            logger.debug(f"Auto-assigned avatar {avatar_code} from Japanese name in: {search_text}")
                            continue
                    
                    # Check aliases with normalization
                    normalized_search = self.avatar_dict._normalize_text(search_text)
                    for alias in avatar.aliases:
                        normalized_alias = self.avatar_dict._normalize_text(alias)
                        if normalized_alias and normalized_alias in normalized_search:
                            ref = self.avatar_dict.get_avatar_ref(avatar_code)
                            if ref and ref not in avatar_refs:
                                avatar_refs.append(ref)
                                logger.debug(f"Auto-assigned avatar {avatar_code} from alias '{alias}' in: {search_text}")
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