from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Literal
from datetime import datetime
from enum import Enum
from ..core import TestBlock

class ItemCategory(str, Enum):
    AVATAR = "avatar"
    OUTFIT = "outfit"
    ACCESSORY = "accessory"
    GIMMICK = "gimmick"
    OTHER = "other"

class TagType(str, Enum):
    COLOR = "color"
    STYLE = "style"
    MOOD = "mood"
    BODY = "body"
    SEASON = "season"
    FUNCTION = "function"
    AVATAR_LINK = "avatar_link"

class TagSource(str, Enum):
    MANUAL = "manual"
    GENERATED = "generated"
    INFERRED = "inferred"

@dataclass(frozen=True)
class AvatarRef:
    code: str
    name: str

@dataclass(frozen=True)
class FileAsset:
    filename: str
    version: Optional[str] = None
    size: Optional[int] = None
    hash: Optional[str] = None

@dataclass(frozen=True)
class Tag:
    tag_id: str
    name: str
    type: TagType
    source: TagSource
    confidence: float = 1.0

@dataclass(frozen=True)
class Item:
    item_id: str
    source: str = "booth"
    source_url: str = ""
    title: str = ""
    description: str = ""
    thumbnail_url: str = ""
    creator_id: str = ""
    creator_name: str = ""
    published_at: Optional[datetime] = None
    tags_raw: List[str] = field(default_factory=list)
    tags_generated: List[str] = field(default_factory=list)
    category: ItemCategory = ItemCategory.OTHER
    like_count: int = 0
    price: Optional[int] = None
    targets: List[AvatarRef] = field(default_factory=list)
    files: List[FileAsset] = field(default_factory=list)
    
    # Compatibility with existing logic
    @property
    def name(self) -> str: return self.title
    @property
    def image_url(self) -> str: return self.thumbnail_url
    @property
    def url(self) -> str: return self.source_url
    @property
    def shop_name(self) -> str: return self.creator_name
    @property
    def current_price(self) -> Optional[int]: return self.price
    @property
    def tags(self) -> List[str]: return self.tags_raw + self.tags_generated
    @property
    def updated_at(self) -> Optional[datetime]: return self.published_at
    @property
    def type(self) -> str: return self.category.value

@dataclass(frozen=True)
class IndexModel:
    item_id: str
    vector_embedding: List[float] = field(default_factory=list)
    tag_index: List[str] = field(default_factory=list) # List of tag_ids
    text_index: str = ""
    filter_index: Dict[str, Any] = field(default_factory=dict) # category, price_bucket, like_bucket, year

@dataclass(frozen=True)
class GraphEdge:
    target_id: str
    relation: Literal["created_by", "has_tag", "similar_to", "used_with"]
    weight: float = 1.0

@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: Literal["item", "creator", "tag"]
    edges: List[GraphEdge] = field(default_factory=list)

# Legacy support/renamed
Node = GraphNode
Edge = GraphEdge

@dataclass(frozen=True)
class TestBlockLog:
    trace_id: str
    block: TestBlock
    timestamp: datetime = field(default_factory=datetime.now)

# Raw Layer
@dataclass(frozen=True)
class RawAssetPage:
    url: str
    content: str
    scraped_at: datetime

@dataclass(frozen=True)
class CrawlLog:
    url: str
    status_code: int
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass(frozen=True)
class AccessLog:
    method: str
    path: str
    status_code: int
    timestamp: datetime = field(default_factory=datetime.now)

# For compatibility with existing registry.py which uses storage.py classes
class ItemType(str, Enum):
    AVATAR = "avatar"
    COSTUME = "outfit" # Map outfit to costume if needed
    ACCESSORY = "accessory"
    TOOL = "gimmick"
    OTHER = "other"
