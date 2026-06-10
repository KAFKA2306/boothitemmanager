import collections
from dataclasses import replace

from ..core import TestBlock
from ..schemas.storage import Item


def calculate_similar_items(items: list[Item], trace_id: str = "default") -> TestBlock:
    if not items:
        return TestBlock(
            trace_id=trace_id,
            input=0,
            pre_state={},
            action="calculate_similarity",
            expected_state={"item_count": 0},
            actual_state={"items": [], "item_count": 0},
            diff={},
            result="SUCCESS",
        )
    inverted_index: dict[str, list[int]] = collections.defaultdict(list)
    category_index: dict[str, list[int]] = collections.defaultdict(list)
    item_tag_sets: list[set[str]] = []
    for idx, item in enumerate(items):
        t_set = set(item.tags)
        item_tag_sets.append(t_set)
        for tag in t_set:
            inverted_index[tag].append(idx)
        category_index[item.category.value].append(idx)
    updated_items = []
    for idx, item in enumerate(items):
        tags = item_tag_sets[idx]
        candidate_counts = collections.Counter()
        for tag in tags:
            for other_idx in inverted_index[tag]:
                if other_idx != idx:
                    candidate_counts[other_idx] += 1
        similarities: list[tuple[str, float]] = []
        candidate_indices = set(candidate_counts.keys())
        if len(candidate_indices) < 10:
            cat_items = category_index.get(item.category.value, [])
            candidate_indices.update(cat_items[:100])
            if idx in candidate_indices:
                candidate_indices.remove(idx)
        top_candidates = [c[0] for c in candidate_counts.most_common(100)]
        if len(top_candidates) < 100:
            remaining = list(candidate_indices - set(top_candidates))
            top_candidates.extend(remaining[: 100 - len(top_candidates)])
        for other_idx in top_candidates:
            other_item = items[other_idx]
            other_tags = item_tag_sets[other_idx]
            intersection_count = len(tags & other_tags)
            union_count = len(tags | other_tags)
            jaccard = intersection_count / union_count if union_count > 0 else 0.0
            score = jaccard
            if item.category == other_item.category:
                score += 0.1
            if score > 0:
                similarities.append((other_item.item_id, score))
        similarities.sort(key=lambda x: (-x[1], x[0]))
        top_5_ids = [s[0] for s in similarities[:5]]
        updated_items.append(replace(item, similar_items=top_5_ids))
    return TestBlock(
        trace_id=trace_id,
        input={"item_count": len(items)},
        pre_state={},
        action="calculate_similar_items",
        expected_state={"processed_count": len(items)},
        actual_state={"items": updated_items, "processed_count": len(updated_items)},
        diff={},
        result="SUCCESS",
    )
