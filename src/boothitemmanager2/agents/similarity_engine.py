import collections
from typing import List, Dict, Set, Tuple
from dataclasses import replace
from ..schemas.storage import Item
from ..core import TestBlock

def calculate_similar_items(items: List[Item], trace_id: str = "default") -> TestBlock:
    """
    アイテム間の類似度を計算するエンジンだよっ！✨
    タグのJaccard係数とカテゴリの同一性を組み合わせて、似ているアイテムを見つけるよ💕
    Zero-Fat & 効率性を重視して、転置インデックスで高速化してるよ！
    """
    if not items:
        return TestBlock(
            trace_id=trace_id,
            input=0,
            pre_state={},
            action="calculate_similarity",
            expected_state={"item_count": 0},
            actual_state={"items": [], "item_count": 0},
            diff={},
            result="SUCCESS"
        )

    # 1. 転置インデックスの作成（タグ -> アイテムインデックス）
    # 全件比較（O(N^2)）を避けるための賢い工夫だよっ！
    inverted_index: Dict[str, List[int]] = collections.defaultdict(list)
    # カテゴリごとのインデックスも作っておくね💕
    category_index: Dict[str, List[int]] = collections.defaultdict(list)
    item_tag_sets: List[Set[str]] = []

    for idx, item in enumerate(items):
        t_set = set(item.tags)
        item_tag_sets.append(t_set)
        for tag in t_set:
            inverted_index[tag].append(idx)
        category_index[item.category.value].append(idx)

    updated_items = []

    # 2. 各アイテムに対して類似アイテムを計算
    for idx, item in enumerate(items):
        tags = item_tag_sets[idx]
        
        # 共通のタグを持つ候補を抽出してカウントするよ✨
        candidate_counts = collections.Counter()
        for tag in tags:
            for other_idx in inverted_index[tag]:
                if other_idx != idx:
                    candidate_counts[other_idx] += 1

        # スコア計算（Jaccard係数 + カテゴリボーナス）
        similarities: List[Tuple[str, float]] = []
        
        # 候補をマージするよ！共通タグがある子たちを優先するね💕
        candidate_indices = set(candidate_counts.keys())
        
        # もし候補が少なかったら、同じカテゴリの子たちも少しだけ混ぜてあげるよっ✨
        if len(candidate_indices) < 10:
            cat_items = category_index.get(item.category.value, [])
            # 多すぎると大変だから、先頭100件くらいから探そうかな💕
            candidate_indices.update(cat_items[:100])
            if idx in candidate_indices:
                candidate_indices.remove(idx)

        # 効率化のために、共通タグが多い上位100件（または全候補）を詳しく調べるね💕
        top_candidates = [c[0] for c in candidate_counts.most_common(100)]
        # 足りない分を candidate_indices から補填
        if len(top_candidates) < 100:
            remaining = list(candidate_indices - set(top_candidates))
            top_candidates.extend(remaining[:(100 - len(top_candidates))])

        for other_idx in top_candidates:
            other_item = items[other_idx]
            other_tags = item_tag_sets[other_idx]
            
            # Jaccard係数 = (共通タグ数) / (全タグの和集合数)
            intersection_count = len(tags & other_tags)
            union_count = len(tags | other_tags)
            jaccard = intersection_count / union_count if union_count > 0 else 0.0
            
            # カテゴリが同じなら、もっと仲良し！スコアをアップするよっ！💕
            score = jaccard
            if item.category == other_item.category:
                score += 0.1
            
            if score > 0:
                similarities.append((other_item.item_id, score))

        # スコア順にソート（スコアが同じならID順で安定させるよ✨）
        similarities.sort(key=lambda x: (-x[1], x[0]))
        top_5_ids = [s[0] for s in similarities[:5]]

        # immutableなItemをreplaceで新しく作り直すよ💕
        updated_items.append(replace(item, similar_items=top_5_ids))

    return TestBlock(
        trace_id=trace_id,
        input={"item_count": len(items)},
        pre_state={},
        action="calculate_similar_items",
        expected_state={"processed_count": len(items)},
        actual_state={
            "items": updated_items,
            "processed_count": len(updated_items)
        },
        diff={},
        result="SUCCESS"
    )
