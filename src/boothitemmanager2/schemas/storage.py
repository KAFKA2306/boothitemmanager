from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal


class ItemCategory(StrEnum):
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
    appearance: list[str] = field(default_factory=list)
    body_type: list[str] = field(default_factory=list)
    style: list[str] = field(default_factory=list)
    color: list[str] = field(default_factory=list)
    outfit_type: list[str] = field(default_factory=list)
    accessory: list[str] = field(default_factory=list)
    feature: list[str] = field(default_factory=list)
    platform: list[str] = field(default_factory=list)
    season: list[str] = field(default_factory=list)
    avatar_link: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AvatarRef:
    code: str
    name: str


@dataclass(frozen=True)
class FileAsset:
    filename: str
    version: str | None = None
    size: int | None = None
    hash: str | None = None


@dataclass(frozen=True)
class Item:
    item_id: str
    source_url: str
    title: str
    description: str
    thumbnail_url: str
    creator_id: str
    creator_name: str
    published_at: datetime | None
    like_count: int
    price: int | None
    category: ItemCategory
    tag_set: TagSet
    similar_items: list[str] = field(default_factory=list)
    user_state: dict[str, Any] = field(default_factory=dict)
    tags_raw: list[str] = field(default_factory=list)
    targets: list[AvatarRef] = field(default_factory=list)
    files: list[FileAsset] = field(default_factory=list)
    source: str = "booth"

    @property
    def tags_generated(self) -> list[str]:
        flattened = []
        for v in self.tag_set.__dict__.values():
            if isinstance(v, list):
                flattened.extend(v)
        return list(set(flattened))

    @property
    def tags(self) -> list[str]:
        flattened = []
        for v in self.tag_set.__dict__.values():
            if isinstance(v, list):
                flattened.extend(v)
        return list(set(self.tags_raw + flattened))


@dataclass(frozen=True)
class TestBlockLog:
    trace_id: str
    block: Any
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
    edges: list[GraphEdge] = field(default_factory=list)


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
    nodes: list[TagNode] = field(default_factory=list)
    edges: list[TagEdge] = field(default_factory=list)


@dataclass(frozen=True)
class IndexModel:
    item_id: str
    vector_embedding: list[float] = field(default_factory=list)
    tag_index: list[str] = field(default_factory=list)
    text_index: str = ""
    filter_index: dict[str, Any] = field(default_factory=dict)
