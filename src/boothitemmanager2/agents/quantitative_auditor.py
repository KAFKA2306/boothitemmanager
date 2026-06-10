from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..schemas.storage import Item

_TOTAL_FEATURES = 4


@dataclass(frozen=True)
class CrawlStats:
    source_items: int | None = None
    indexed_items: int | None = None


@dataclass(frozen=True)
class FilterEvidence:
    year_filter_count: int | None = None
    popularity_filter_count: int | None = None
    category_filter_count: int | None = None


@dataclass(frozen=True)
class FeatureStats:
    color_search: int | None = None
    style_search: int | None = None
    avatar_reverse_search: int | None = None
    cross_category_search: int | None = None


@dataclass(frozen=True)
class _FilterResult:
    status: str
    evidence_count: int


@dataclass(frozen=True)
class AuditReport:
    total_items: int
    items_with_metadata: int
    items_with_tags: int
    items_missing_fields: int
    coverage_rate: float
    tagging_rate: float
    missing_rate: float
    tagged_items: int
    invalid_tags: int
    duplicate_tags: int
    multi_label_conflicts: int
    valid_tag_rate: float
    source_items: int
    indexed_items: int
    lost_items: int
    sync_rate: float
    year_filter: _FilterResult
    popularity_filter: _FilterResult
    category_filter: _FilterResult
    color_search: int
    style_search: int
    avatar_reverse_search: int
    cross_category_search: int
    feature_coverage_score: float
    final_score: float


_REQUIRED_FIELDS = ("item_id", "source", "title", "creator_name", "thumbnail_url", "source_url")


def _has_metadata(item: Item) -> bool:
    return all(bool(getattr(item, f, None)) for f in _REQUIRED_FIELDS)


def _count_invalid_tags(item: Item) -> int:
    return sum(1 for t in item.tags if not t or not t.strip())


def _count_duplicate_tags(item: Item) -> int:
    seen: set[str] = set()
    dupes = 0
    for t in item.tags:
        if t in seen:
            dupes += 1
        seen.add(t)
    return dupes


def _has_multi_label_conflict(item: Item) -> bool:
    codes = [r.code for r in item.targets]
    return len(codes) != len(set(codes))


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _filter_result(count: int | None) -> _FilterResult:
    if count is None:
        return _FilterResult(status="UNKNOWN", evidence_count=0)
    if count > 0:
        return _FilterResult(status="PASS", evidence_count=count)
    return _FilterResult(status="FAIL", evidence_count=0)


def _feature_support_count(val: int | None) -> int:
    return val if val is not None else 0


def _count_supported_features(*vals: int | None) -> int:
    return sum(1 for v in vals if v is not None and v > 0)


class QuantitativeAuditor:
    def run(
        self,
        items: Sequence[Item],
        crawl: CrawlStats | None = None,
        filters: FilterEvidence | None = None,
        features: FeatureStats | None = None,
    ) -> AuditReport:
        crawl = crawl or CrawlStats()
        filters = filters or FilterEvidence()
        features = features or FeatureStats()
        total = len(items)
        with_meta = sum(1 for i in items if _has_metadata(i))
        with_tags = sum(1 for i in items if i.tags)
        missing = sum(1 for i in items if not _has_metadata(i))
        tagged = with_tags
        invalid = sum(_count_invalid_tags(i) for i in items)
        dupes = sum(_count_duplicate_tags(i) for i in items)
        conflicts = sum(1 for i in items if _has_multi_label_conflict(i))
        valid_tag = _safe_rate(max(tagged - invalid, 0), tagged) if tagged > 0 else 0.0
        src = crawl.source_items if crawl.source_items is not None else 0
        idx = crawl.indexed_items if crawl.indexed_items is not None else total
        lost = max(src - idx, 0) if src > 0 else 0
        sync = _safe_rate(idx, src) if src > 0 else 0.0
        year_f = _filter_result(filters.year_filter_count)
        pop_f = _filter_result(filters.popularity_filter_count)
        cat_f = _filter_result(filters.category_filter_count)
        color_n = _feature_support_count(features.color_search)
        style_n = _feature_support_count(features.style_search)
        avatar_rev_n = _feature_support_count(features.avatar_reverse_search)
        cross_n = _feature_support_count(features.cross_category_search)
        supported = _count_supported_features(
            features.color_search,
            features.style_search,
            features.avatar_reverse_search,
            features.cross_category_search,
        )
        feat_score = _safe_rate(supported, _TOTAL_FEATURES)
        coverage_rate = _safe_rate(with_meta, total)
        tagging_rate = _safe_rate(with_tags, total)
        final_score = round(
            coverage_rate * 0.25 + tagging_rate * 0.25 + sync * 0.25 + feat_score * 0.25, 4
        )
        return AuditReport(
            total_items=total,
            items_with_metadata=with_meta,
            items_with_tags=with_tags,
            items_missing_fields=missing,
            coverage_rate=coverage_rate,
            tagging_rate=tagging_rate,
            missing_rate=_safe_rate(missing, total),
            tagged_items=tagged,
            invalid_tags=invalid,
            duplicate_tags=dupes,
            multi_label_conflicts=conflicts,
            valid_tag_rate=valid_tag,
            source_items=src,
            indexed_items=idx,
            lost_items=lost,
            sync_rate=sync,
            year_filter=year_f,
            popularity_filter=pop_f,
            category_filter=cat_f,
            color_search=color_n,
            style_search=style_n,
            avatar_reverse_search=avatar_rev_n,
            cross_category_search=cross_n,
            feature_coverage_score=feat_score,
            final_score=final_score,
        )


def format_report(r: AuditReport) -> str:
    lines: list[str] = [
        "---",
        "",
        "【1. データカバレッジ監査】",
        "",
        f"total_items: {r.total_items}",
        f"items_with_metadata: {r.items_with_metadata}",
        f"items_with_tags: {r.items_with_tags}",
        f"items_missing_fields: {r.items_missing_fields}",
        "",
        f"coverage_rate = {r.coverage_rate}",
        f"tagging_rate = {r.tagging_rate}",
        f"missing_rate = {r.missing_rate}",
        "",
        "---",
        "",
        "【2. タグ生成品質】",
        "",
        f"tagged_items: {r.tagged_items}",
        f"invalid_tags: {r.invalid_tags}",
        f"duplicate_tags: {r.duplicate_tags}",
        f"multi_label_conflicts: {r.multi_label_conflicts}",
        "",
        f"valid_tag_rate = {r.valid_tag_rate}",
        "",
        "---",
        "",
        "【3. クロール整合性】",
        "",
        f"source_items: {(r.source_items if r.source_items else 'Unknown')}",
        f"indexed_items: {r.indexed_items}",
        f"lost_items: {r.lost_items}",
        "",
        f"sync_rate = {(r.sync_rate if r.source_items else 'Unknown')}",
        "",
        "---",
        "",
        "【4. フィルタ制約監査】",
        "",
        "constraints:",
        "",
        "* year_filter_applied:",
        f"  status: {r.year_filter.status}",
        f"  evidence_count: {r.year_filter.evidence_count}",
        "",
        "* popularity_filter_applied:",
        f"  status: {r.popularity_filter.status}",
        f"  evidence_count: {r.popularity_filter.evidence_count}",
        "",
        "* category_filter_applied:",
        f"  status: {r.category_filter.status}",
        f"  evidence_count: {r.category_filter.evidence_count}",
        "",
        "---",
        "",
        "【5. 検索機能カバレッジ】",
        "",
        "features:",
        "",
        f"* color_search: {r.color_search}_items_supported",
        f"* style_search: {r.style_search}_items_supported",
        f"* avatar_reverse_search: {r.avatar_reverse_search}_items_supported",
        f"* cross_category_search: {r.cross_category_search}_items_supported",
        "",
        f"feature_coverage_score = {r.feature_coverage_score}",
        "",
        "---",
        "",
        "【6. データ信頼度スコア】",
        "",
        "final_score =",
        f"({r.coverage_rate} × 0.25) +",
        f"({r.tagging_rate} × 0.25) +",
        f"({r.sync_rate} × 0.25) +",
        f"({r.feature_coverage_score} × 0.25)",
        f"= {r.final_score}",
        "",
        "---",
    ]
    return "\n".join(lines)
