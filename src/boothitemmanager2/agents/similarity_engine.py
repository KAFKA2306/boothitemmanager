from typing import List, Dict, Set
from dataclasses import replace
from ..schemas.storage import Item
import collections

def compute_similar_items(items: List[Item]) -> List[Item]:
    """
    Computes top 5 similar items for each item based on tags and targets.
    Uses an inverted index to avoid O(N^2) complexity.
    Zero-Fat, Crash-Driven.
    """
    if not items:
        return []

    # 1. Precompute tag sets and inverted index
    item_tags: Dict[str, Set[str]] = {}
    inverted_index: Dict[str, List[str]] = collections.defaultdict(list)

    for item in items:
        # Combine tags_generated and target codes
        tags = set(item.tags_generated)
        for target in item.targets:
            tags.add(f"target:{target.code}")
        
        item_tags[item.item_id] = tags
        for tag in tags:
            inverted_index[tag].append(item.item_id)

    updated_items = []

    # 2. Compute similarity for each item
    for item in items:
        tags = item_tags[item.item_id]
        if not tags:
            updated_items.append(item)
            continue

        # Find candidates sharing at least one tag
        candidates_counts = collections.Counter()
        for tag in tags:
            for other_id in inverted_index[tag]:
                if other_id != item.item_id:
                    candidates_counts[other_id] += 1

        # Calculate Jaccard similarity for top candidates
        # To further optimize, we only consider candidates with the highest intersection
        # but for top 5, intersection count might be enough or we can calculate Jaccard for top N intersections.
        similarities = []
        # Take up to 100 top intersection candidates to calculate full Jaccard
        for other_id, intersection_count in candidates_counts.most_common(100):
            other_tags = item_tags[other_id]
            union_count = len(tags | other_tags)
            jaccard = intersection_count / union_count if union_count > 0 else 0
            similarities.append((other_id, jaccard))

        # Sort by Jaccard score (desc) and then by item_id (asc) for stability
        similarities.sort(key=lambda x: (-x[1], x[0]))
        top_5_ids = [s[0] for s in similarities[:5]]

        updated_items.append(replace(item, similar_items=top_5_ids))

    return updated_items
