from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Literal
from datetime import datetime
from enum import Enum

class ItemCategory(str, Enum):
    AVATAR = "AVATAR"
    OUTFIT = "OUTFIT"
    ACCESSORY = "ACCESSORY"
    TEXTURE = "TEXTURE"
    PROP = "PROP"
    GIMMICK_TOOL = "GIMMICK_TOOL"
    HAIRSTYLE = "HAIRSTYLE"
    WORLD = "WORLD"
    ANIMATION = "ANIMATION"
    VROID = "VROID"
    ASSET = "ASSET"

@dataclass(frozen=True)
class TagSet:
    appearance: List[str] = field(default_factory=list)
    body_type: List[str] = field(default_factory=list)
    style: List[str] = field(default_factory=list)
    color: List[str] = field(default_factory=list)
    outfit_type: List[str] = field(default_factory=list)
    accessory: List[str] = field(default_factory=list)
    feature: List[str] = field(default_factory=list)
    platform: List[str] = field(default_factory=list)
    season: List[str] = field(default_factory=list)
    avatar_link: List[str] = field(default_factory=list)

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
class Item:
    item_id: str
    source_url: str
    title: str
    description: str
    thumbnail_url: str
    creator_id: str
    creator_name: str
    published_at: Optional[datetime]
    like_count: int
    price: Optional[int]
    category: ItemCategory
    tag_set: TagSet
    similar_items: List[str] = field(default_factory=list)
    user_state: Dict[str, Any] = field(default_factory=dict)
    
    # Extended metadata
    tags_raw: List[str] = field(default_factory=list)
    targets: List[AvatarRef] = field(default_factory=list)
    files: List[FileAsset] = field(default_factory=list)
    source: str = "booth"

    @property
    def tags_generated(self) -> List[str]:
        # Flatten tag_set for compatibility
        flattened = []
        for v in self.tag_set.__dict__.values():
            if isinstance(v, list):
                flattened.extend(v)
        return list(set(flattened))

    @property
    def tags(self) -> List[str]:
        # Flatten tag_set for legacy compatibility
        flattened = []
        for v in self.tag_set.__dict__.values():
            if isinstance(v, list):
                flattened.extend(v)
        return list(set(self.tags_raw + flattened))

@dataclass(frozen=True)
class TestBlockLog:
    trace_id: str
    block: Any # Avoid circular import if possible, or use Any
    timestamp: datetime = field(default_factory=datetime.now)

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

@dataclass(frozen=True)
class TagNode:
    tag_id: str
    name: str
    dimension: str = "general"
    weight: int = 0

@dataclass(frozen=True)
class TagEdge:
    source_id: str
    target_id: str
    strength: float

@dataclass(frozen=True)
class TagGraph:
    nodes: List[TagNode] = field(default_factory=list)
    edges: List[TagEdge] = field(default_factory=list)

@dataclass(frozen=True)
class IndexModel:
    item_id: str
    vector_embedding: List[float] = field(default_factory=list)
    tag_index: List[str] = field(default_factory=list)
    text_index: str = ""
    filter_index: Dict[str, Any] = field(default_factory=dict)
