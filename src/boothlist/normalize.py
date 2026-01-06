import logging
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass
class AvatarRef:
    code: str
    name: str


@dataclass
class FileAsset:
    filename: str
    version: str | None = None
    size: int | None = None
    hash: str | None = None


@dataclass
class Item:
    item_id: int
    type: str
    name: str
    shop_name: str | None = None
    creator_id: str | None = None
    image_url: str | None = None
    url: str | None = None
    current_price: int | None = None
    description_excerpt: str | None = None
    files: list[FileAsset] = None
    targets: list[AvatarRef] = None
    tags: list[str] = None
    updated_at: str | None = None
    variants: list["Variant"] = None

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
    subitem_id: str
    parent_item_id: int
    variant_name: str
    targets: list[AvatarRef] = None
    files: list[FileAsset] = None
    notes: str | None = None

    def __post_init__(self):
        if self.targets is None:
            self.targets = []
        if self.files is None:
            self.files = []


@dataclass
class Avatar:
    code: str
    name_ja: str
    aliases: list[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


class AvatarDictionary:
    def __init__(self, aliases_file: str = "aliases.yml"):
        self.aliases_file = aliases_file
        self.avatars = {}
        self.alias_to_code = {}
        self.type_aliases = {}
        self.options = {}
        self._load_aliases()

    def _load_aliases(self):
        aliases_path = Path(self.aliases_file)
        if not aliases_path.exists():
            self._load_hardcoded_avatars()
            return

        with open(aliases_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.options = data.get("options", {})
        avatars_data = data.get("avatars", {})
        for code, avatar_data in avatars_data.items():
            avatar = Avatar(
                code=code,
                name_ja=avatar_data.get("name_ja", code),
                aliases=avatar_data.get("aliases", []),
            )
            self.avatars[code] = avatar

        types_data = data.get("types", {})
        for type_name, type_data in types_data.items():
            self.type_aliases[type_name] = type_data.get("aliases", [])

        self._build_alias_lookup()

    def _load_hardcoded_avatars(self):
        self.avatars = {
            "Selestia": Avatar(
                code="Selestia",
                name_ja="セレスティア",
                aliases=["セレスティア", "selestia", "SELESTIA", "Celestia"],
            ),
            "Kikyo": Avatar(
                code="Kikyo", name_ja="桔梗", aliases=["桔梗", "kikyo", "KIKYO", "kikyou", "Kikyou"]
            ),
            "Kanae": Avatar(
                code="Kanae", name_ja="かなえ", aliases=["かなえ", "kanae", "KANAE", "カナエ"]
            ),
            "Shinano": Avatar(
                code="Shinano", name_ja="しなの", aliases=["しなの", "shinano", "SHINANO", "シナノ"]
            ),
            "Manuka": Avatar(
                code="Manuka", name_ja="マヌカ", aliases=["マヌカ", "manuka", "MANUKA"]
            ),
            "Moe": Avatar(code="Moe", name_ja="萌", aliases=["萌", "moe", "MOE"]),
            "Rurune": Avatar(
                code="Rurune", name_ja="ルルネ", aliases=["ルルネ", "rurune", "RURUNE"]
            ),
            "Hakka": Avatar(code="Hakka", name_ja="薄荷", aliases=["薄荷", "hakka", "HAKKA"]),
            "Mizuki": Avatar(code="Mizuki", name_ja="瑞希", aliases=["瑞希", "mizuki", "MIZUKI"]),
            "SUN": Avatar(code="SUN", name_ja="SUN", aliases=["SUN", "Sun", "サン"]),
            "INABA": Avatar(
                code="INABA", name_ja="INABA", aliases=["INABA", "Inaba", "いなば", "イナバ"]
            ),
            "Shiina": Avatar(
                code="Shiina",
                name_ja="椎名",
                aliases=["椎名", "Shiina", "SHIINA", "しいな", "シイナ"],
            ),
            "KitsuneAme": Avatar(
                code="KitsuneAme",
                name_ja="狐雨",
                aliases=["狐雨", "kitsuneame", "KITSUNEAME", "キツネアメ", "きつねあめ"],
            ),
            "NekoMaid": Avatar(
                code="NekoMaid",
                name_ja="猫メイド",
                aliases=[
                    "猫メイド",
                    "ネコメイド",
                    "nekomaid",
                    "NekoMaid",
                    "neko maid",
                    "ネコ メイド",
                ],
            ),
        }
        self._build_alias_lookup()

    def _build_alias_lookup(self):
        self.alias_to_code = {}
        for avatar in self.avatars.values():
            normalized_code = self._normalize_text(avatar.code)
            self.alias_to_code[avatar.code] = avatar.code
            self.alias_to_code[normalized_code] = avatar.code
            for alias in avatar.aliases:
                normalized_alias = self._normalize_text(alias)
                self.alias_to_code[alias] = avatar.code
                self.alias_to_code[normalized_alias] = avatar.code

    def _normalize_text(self, text: str) -> str:
        if not text:
            return text
        if self.options.get("unicode_normalization") == "NFKC":
            text = unicodedata.normalize("NFKC", text)
        if self.options.get("case_insensitive", True):
            text = text.lower()
        if self.options.get("trim_whitespace", True):
            text = text.strip()
        if self.options.get("collapse_inner_spaces", True):
            text = re.sub(r"\s+", " ", text)
        strip_symbols = self.options.get("strip_symbols", [])
        for symbol in strip_symbols:
            text = text.replace(symbol, "")
        return text

    def normalize_avatar(self, avatar_text: str) -> str | None:
        if not avatar_text:
            return None
        if avatar_text in self.alias_to_code:
            return self.alias_to_code[avatar_text]
        normalized_text = self._normalize_text(avatar_text)
        if normalized_text in self.alias_to_code:
            return self.alias_to_code[normalized_text]
        bracket_pattern = r"[「【\(]([^」】\)]+)[」】\)]"
        match = re.search(bracket_pattern, avatar_text)
        if match:
            bracket_content = self._normalize_text(match.group(1))
            if bracket_content in self.alias_to_code:
                return self.alias_to_code[bracket_content]
        return None

    def get_avatar_ref(self, code: str) -> AvatarRef | None:
        avatar = self.avatars.get(code)
        if avatar:
            return AvatarRef(code=avatar.code, name=avatar.name_ja)
        return None


class DataNormalizer:
    CATEGORY_MAPPING = {
        "3D Avatar": "avatar",
        "3D Clothing": "costume",
        "3D Accessory": "accessory",
        "Tool": "tool",
        "Gimmick": "gimmick",
        "gimick": "gimmick",
        "World": "world",
        "Texture": "texture",
        "texture": "texture",
        "TEXTURE": "texture",
        "Scenario": "scenario",
        "Bundle": "bundle",
        "Goods": "other",
        "GOODS": "other",
        "アバター": "avatar",
        "衣装": "costume",
        "アクセサリ": "accessory",
        "アクセサリー": "accessory",
        "ツール": "tool",
        "ギミック": "gimmick",
        "ワールド": "world",
        "テクスチャ": "texture",
        "素材": "texture",
        "シナリオ": "scenario",
        "セット": "bundle",
        "グッズ": "other",
    }

    def __init__(self):
        self.avatar_dict = AvatarDictionary()

    def normalize_type(self, category: str | None) -> str:
        if not category:
            return "other"
        if self.avatar_dict.type_aliases:
            normalized_category = self.avatar_dict._normalize_text(category)
            for type_name, aliases in self.avatar_dict.type_aliases.items():
                if category in aliases:
                    return type_name
                normalized_aliases = [self.avatar_dict._normalize_text(alias) for alias in aliases]
                if normalized_category in normalized_aliases:
                    return type_name
        if category in self.CATEGORY_MAPPING:
            return self.CATEGORY_MAPPING[category]
        for key, value in self.CATEGORY_MAPPING.items():
            if category.lower() == key.lower():
                return value
        category_lower = category.lower()
        if "avatar" in category_lower or "アバター" in category_lower:
            return "avatar"
        elif "costume" in category_lower or "衣装" in category_lower:
            return "costume"
        elif "accessor" in category_lower or "アクセサリ" in category_lower:
            return "accessory"
        elif "tool" in category_lower or "ツール" in category_lower:
            return "tool"
        elif "world" in category_lower or "ワールド" in category_lower:
            return "world"
        return "other"

    def normalize_files(self, file_list: list[str]) -> list[FileAsset]:
        if not file_list:
            return []
        assets = []
        for filename in file_list:
            if not filename:
                continue
            assets.append(FileAsset(filename=filename, version=self._extract_version(filename)))
        return assets

    def _extract_version(self, filename: str) -> str | None:
        version_patterns = [
            r"[vV](\d+(?:\.\d+)*)",
            r"Ver(\d+(?:\.\d+)*)",
            r"ver(\d+(?:\.\d+)*)",
            r"V(\d+(?:\.\d+)*)",
            r"_(\d+\.\d+)(?:\.|_|$)",
        ]
        for pattern in version_patterns:
            if match := re.search(pattern, filename):
                return match.group(1)
        return None

    def extract_avatar_targets(
        self, name: str, files: list[str], description: str | None = None
    ) -> list[AvatarRef]:
        avatar_codes = set()
        for filename in files:
            for avatar_code in self.avatar_dict.avatars.keys():
                avatar_lower = avatar_code.lower()
                filename_lower = filename.lower()
                if filename_lower.startswith(f"{avatar_lower}_"):
                    avatar_codes.add(avatar_code)
                    continue
                if f"_{avatar_lower}" in filename_lower:
                    avatar_codes.add(avatar_code)
                    continue
                version_patterns = [
                    rf"{re.escape(avatar_lower)}[_\s]*v\d",
                    rf"\d+_{re.escape(avatar_lower)}_ver",
                    rf"{re.escape(avatar_lower)}ver",
                ]
                for pattern in version_patterns:
                    if re.search(pattern, filename_lower):
                        avatar_codes.add(avatar_code)
                        break
                avatar = self.avatar_dict.avatars[avatar_code]
                if avatar.name_ja and avatar.name_ja in filename:
                    avatar_codes.add(avatar_code)

        combined_text = (name or "") + " " + (description or "")
        japanese_patterns = [
            r"対応アバター[：:]\s*([^。\n]+)",
            r"対応[：:]?\s*([^。\n]*(?:セレスティア|桔梗|かなえ|しなの|マヌカ|萌|ルルネ|薄荷|瑞希|SUN|INABA|椎名|狐雨|猫メイド|シアン|真冬|myu65|めいゆん|フィオナ|森羅|Bow)[^。\n]*)",
            r"「([^」]+)」",
            r"【([^】]+)】",
            r"『([^』]+)』",
        ]
        for pattern in japanese_patterns:
            for match in re.findall(pattern, combined_text, re.IGNORECASE):
                for avatar_code in self.avatar_dict.avatars.keys():
                    avatar = self.avatar_dict.avatars[avatar_code]
                    if avatar.name_ja and avatar.name_ja in match:
                        avatar_codes.add(avatar_code)
                    if self.avatar_dict.normalize_avatar(match.strip()) == avatar_code:
                        avatar_codes.add(avatar_code)

        english_patterns = [
            r"for\s+(Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki|SUN|INABA|Shiina|KitsuneAme|NekoMaid|Cian|Mafuyu|myu65|Meiyun|Fiona|Shinra|Bow)",
            r"(Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki|SUN|INABA|Shiina|KitsuneAme|NekoMaid|Cian|Mafuyu|myu65|Meiyun|Fiona|Shinra|Bow)\s*用",
            r"(Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki|SUN|INABA|Shiina|KitsuneAme|NekoMaid|Cian|Mafuyu|myu65|Meiyun|Fiona|Shinra|Bow)\s+compatible",
        ]
        for pattern in english_patterns:
            for match in re.findall(pattern, combined_text, re.IGNORECASE):
                if normalized := self.avatar_dict.normalize_avatar(match):
                    avatar_codes.add(normalized)

        return [ref for code in avatar_codes if (ref := self.avatar_dict.get_avatar_ref(code))]

    def normalize_item(self, raw_item, metadata) -> Item:
        name = metadata.name or raw_item.name or f"Item {raw_item.item_id}"
        item_type = self.normalize_type(raw_item.category)
        if item_type == "other":
            item_type = self._infer_type_from_text(name, metadata.description_excerpt)
        elif item_type == "avatar" and raw_item.category in [
            "3D Avatar",
            "3D avatar",
            "3Dアバター",
        ]:
            inferred_type = self._infer_type_from_text(name, metadata.description_excerpt)
            if inferred_type != "other":
                item_type = inferred_type

        file_list = metadata.files if metadata.files else raw_item.files
        normalized_files = self.normalize_files(file_list)
        targets = self.extract_avatar_targets(
            name=name, files=file_list, description=metadata.description_excerpt
        )
        if item_type == "avatar" and not targets:
            targets = self._auto_assign_avatar_targets(name, metadata.description_excerpt)

        item = Item(
            item_id=raw_item.item_id,
            type=item_type,
            name=name,
            shop_name=metadata.shop_name,
            creator_id=metadata.creator_id,
            image_url=metadata.image_url,

            url=f"https://booth.pm/ja/items/{raw_item.item_id}",
            current_price=metadata.current_price,
            description_excerpt=metadata.description_excerpt,
            files=normalized_files,
            targets=targets,
            tags=[],
            updated_at=metadata.page_updated_at
            or metadata.scraped_at
            or datetime.now().isoformat(),
        )
        item.variants = self.generate_variants(item)
        return item

    def _infer_type_from_text(self, name: str, description: str | None) -> str:
        combined_text = ((name or "") + " " + (description or "")).lower()
        type_keywords = {
            "gimmick": {
                "priority": 10,
                "keywords": [
                    "gimmick",
                    "gimick",
                    "ギミック",
                    "modularavatar",
                    "モジュラーアバター",
                    "system",
                    "システム",
                    "仕組み",
                    "機能",
                    "寝返り",
                    "ovr",
                    "アニメーション制御",
                    "プロファイル",
                ],
            },
            "tool": {
                "priority": 9,
                "keywords": [
                    "tool",
                    "ツール",
                    "unity",
                    "editor",
                    "エディタ",
                    "インストーラ",
                    "installer",
                    "script",
                    "スクリプト",
                    "unitypackage",
                    "ユニティ",
                ],
            },
            "world": {
                "priority": 8,
                "keywords": [
                    "vrchatワールド",
                    "vrcワールド",
                    "ワールドデータ",
                    "world asset",
                    "ワールドアセット",
                    "背景ステージ",
                    "撮影ステージ",
                ],
            },
            "texture": {
                "priority": 7,
                "keywords": [
                    "texture",
                    "テクスチャ",
                    "素材",
                    "material",
                    "skin",
                    "スキン",
                    "nail",
                    "ネイル",
                    "肌",
                    "ボディ",
                    "ボディテクスチャ",
                    "顔",
                    "フェイス",
                    "リップ",
                    "唇",
                    "眉",
                    "まゆ",
                    "瞳",
                    "目",
                    "虹彩",
                ],
            },
            "accessory": {
                "priority": 6,
                "keywords": [
                    "accessory",
                    "アクセサリ",
                    "アクセサリー",
                    "hair",
                    "ヘア",
                    "髪型",
                    "hat",
                    "帽子",
                    "glasses",
                    "メガネ",
                    "ピアス",
                    "イヤリング",
                    "靴",
                    "シューズ",
                ],
            },
            "costume": {
                "priority": 5,
                "keywords": [
                    "costume",
                    "衣装",
                    "clothing",
                    "dress",
                    "outfit",
                    "コスチューム",
                    "ワンピース",
                    "服装",
                    "ドレス",
                    "スカート",
                    "水着",
                    "浴衣",
                    "セーラー",
                    "メイド服",
                    "シャツ",
                    "ニット",
                    "ビキニ",
                    "bikini",
                    "shirt",
                    "knit",
                    "パーカー",
                    "ジャケット",
                    "コート",
                    "パンツ",
                    "アバター対応",
                    "ベイル",
                    "veil",
                ],
            },
            "avatar": {
                "priority": 11,
                "keywords": [
                    "オリジナル3dアバター",
                    "オリジナル3dモデル",
                    "オリジナルアバター",
                    "3dアバター",
                    "3d avatar",
                    "vrchat向け",
                    "avatar本体",
                ],
            },
            "scenario": {
                "priority": 3,
                "keywords": [
                    "scenario",
                    "シナリオ",
                    "story",
                    "ストーリー",
                    "物語",
                    "台本",
                    "セリフ",
                ],
            },
            "bundle": {
                "priority": 2,
                "keywords": [
                    "bundle",
                    "セット",
                    "セット商品",
                    "フルセット",
                    "full set",
                    "パック",
                    "pack",
                    "コレクション",
                    "collection",
                ],
            },
            "other": {
                "priority": 1,
                "keywords": ["goods", "グッズ", "物販", "アクスタ", "ステッカー"],
            },
        }
        type_scores = {}
        for item_type, config in type_keywords.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in combined_text:
                    score += config["priority"] * 10
            if score > 0:
                type_scores[item_type] = score

        if "3dモデル" in combined_text or "3d model" in combined_text:
            strong_avatar_indicators = [
                "オリジナル3dモデル",
                "オリジナルアバター",
                "original avatar",
                "vrchat向け　オリジナルアバター",
                "アバター本体",
                "3dキャラクター",
                "character model",
                "base model",
                "アバターモデル",
                "3dモデルお買い得セット",
                "vrc上での使用を想定",
                "3dモデル.*セット",
                "お買い得セット.*3dモデル",
            ]
            strong_avatar_score = sum(
                50 for indicator in strong_avatar_indicators if indicator in combined_text
            )
            if strong_avatar_score > 0:
                type_scores["avatar"] = type_scores.get("avatar", 0) + strong_avatar_score
            else:
                costume_indicators = [
                    "衣装",
                    "服",
                    "clothing",
                    "着せ替え",
                    "ウェア",
                    "wear",
                    "dress",
                    "服の形",
                    "服装",
                    "outfit",
                    "ファッション",
                    "fashion",
                    "costume",
                    "構造が複雑",
                    "フィジックスボーン",
                    "着用",
                    "試着",
                    "halloween edition",
                    "for minase",
                    "for [a-z]+",
                    "puppet",
                    "bonny",
                    "ハロウィン",
                    "衣装.*テクスチャ",
                    "衣装.*の.*テクスチャ",
                ]
                costume_score = 0
                for indicator in costume_indicators:
                    if indicator in combined_text:
                        costume_score += 20
                for_pattern_matches = re.findall(r"for\s+([a-z]+)", combined_text, re.IGNORECASE)
                if for_pattern_matches:
                    costume_score += 30 * len(for_pattern_matches)
                if costume_score > 0:
                    type_scores["costume"] = type_scores.get("costume", 0) + costume_score + 50

        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])
            return best_type[0]

        return "other"

    def _auto_assign_avatar_targets(self, name: str, description: str | None) -> list[AvatarRef]:
        avatar_refs = []
        combined_text = (name or "") + " " + (description or "")

        patterns_to_try = [
            r"「([^」]+)」",
            r"【([^】]+)】",
            r"([A-Za-z][A-Za-z0-9]*)[\s_]*[vV]?\d",
            combined_text,
        ]

        for pattern in patterns_to_try:
            if pattern == combined_text:
                search_texts = [combined_text]
            else:
                matches = re.findall(pattern, combined_text)
                search_texts = matches if matches else []

            for search_text in search_texts:
                for avatar_code, avatar in self.avatar_dict.avatars.items():
                    if avatar_code.lower() in search_text.lower():
                        ref = self.avatar_dict.get_avatar_ref(avatar_code)
                        if ref and ref not in avatar_refs:
                            avatar_refs.append(ref)
                            continue

                    if avatar.name_ja in search_text:
                        ref = self.avatar_dict.get_avatar_ref(avatar_code)
                        if ref and ref not in avatar_refs:
                            avatar_refs.append(ref)
                            continue

                    normalized_search = self.avatar_dict._normalize_text(search_text)
                    for alias in avatar.aliases:
                        normalized_alias = self.avatar_dict._normalize_text(alias)
                        if normalized_alias and normalized_alias in normalized_search:
                            ref = self.avatar_dict.get_avatar_ref(avatar_code)
                            if ref and ref not in avatar_refs:
                                avatar_refs.append(ref)
                                break

        return avatar_refs

    def generate_variants(self, item: Item) -> list[Variant]:
        variants = []

        if not self._is_potential_set_item(item):
            return variants

        avatar_variants = self._extract_avatar_variants_from_files(item)
        variants.extend(avatar_variants)

        text_variants = self._extract_variants_from_text(item)
        variants.extend(text_variants)

        variants = self._deduplicate_variants(variants)

        return variants

    def _is_potential_set_item(self, item: Item) -> bool:
        set_keywords = [
            "set",
            "セット",
            "pack",
            "パック",
            "bundle",
            "バンドル",
            "collection",
            "コレクション",
        ]
        name_lower = (item.name or "").lower()

        for keyword in set_keywords:
            if keyword in name_lower:
                return True

        if len(item.targets) > 1:
            return True

        avatar_prefixes = set()
        for file_asset in item.files:
            for avatar_code in self.avatar_dict.avatars.keys():
                if file_asset.filename.lower().startswith(avatar_code.lower() + "_"):
                    avatar_prefixes.add(avatar_code)

        if len(avatar_prefixes) > 1:
            return True

        return False

    def _extract_avatar_variants_from_files(self, item: Item) -> list[Variant]:
        variants = []
        avatar_files = defaultdict(list)

        for file_asset in item.files:
            filename = file_asset.filename.lower()
            for avatar_code in self.avatar_dict.avatars.keys():
                avatar_lower = avatar_code.lower()
                if filename.startswith(avatar_lower + "_"):
                    avatar_files[avatar_code].append(file_asset)
                    break

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
                        notes=f"Files: {', '.join([f.filename for f in files[:3]])}"
                        + ("..." if len(files) > 3 else ""),
                    )
                    variants.append(variant)

        return variants

    def _extract_variants_from_text(self, item: Item) -> list[Variant]:
        variants = []

        if not item.description_excerpt:
            return variants

        patterns = [
            r"対応[アバター]*[：:]\s*([^。\n]+)",
            r"Compatible\s+with[：:]?\s*([^.\n]+)",
            r"for\s+([^.\n]*(?:Selestia|Kikyo|Kanae|Shinano|Manuka|Moe|Rurune|Hakka|Mizuki|Cian|Mafuyu|myu65|Meiyun|Fiona|Shinra|Bow)[^.\n]*)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, item.description_excerpt, re.IGNORECASE)
            for match in matches:
                mentioned_avatars = []
                for avatar_code in self.avatar_dict.avatars.keys():
                    avatar = self.avatar_dict.avatars[avatar_code]
                    if (
                        avatar_code.lower() in match.lower()
                        or avatar.name_ja in match
                        or any(alias.lower() in match.lower() for alias in avatar.aliases)
                    ):
                        mentioned_avatars.append(avatar_code)

                for avatar_code in mentioned_avatars:
                    avatar_ref = self.avatar_dict.get_avatar_ref(avatar_code)
                    if avatar_ref:
                        variant_name = f"{item.name} for {avatar_ref.name}"
                        variant_id = self.generate_variant_id(
                            item.item_id, avatar_code, variant_name
                        )

                        variant = Variant(
                            subitem_id=variant_id,
                            parent_item_id=item.item_id,
                            variant_name=variant_name,
                            targets=[avatar_ref],
                            files=[],
                            notes="Extracted from description text",
                        )
                        variants.append(variant)

        return variants

    def _deduplicate_variants(self, variants: list[Variant]) -> list[Variant]:
        seen_ids = set()
        unique_variants = []

        for variant in variants:
            if variant.subitem_id not in seen_ids:
                seen_ids.add(variant.subitem_id)
                unique_variants.append(variant)

        return unique_variants

    def create_slug(self, text: str) -> str:
        if not text:
            return "unknown"

        slug = text.lower()

        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_-]+", "-", slug)

        slug = slug.strip("-")

        if len(slug) > 50:
            slug = slug[:50].rstrip("-")

        return slug or "unknown"

    def generate_variant_id(self, parent_item_id: int, avatar_code: str, variant_name: str) -> str:
        slug = self.create_slug(variant_name)
        return f"{parent_item_id}#variant:{avatar_code}:{slug}"

    def _build_canonical_url(self, canonical_path: str | None) -> str | None:
        if not canonical_path:
            return None
        return f"https://booth.pm{canonical_path}"
