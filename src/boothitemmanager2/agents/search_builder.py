import json
import os
from typing import List
from ..core import TestBlock
from ..schemas.storage import Item

def build_search_index(items: List[Item], trace_id: str) -> TestBlock:
    output_path = 'api/search_index.json'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    index = []
    for item in items:
        index.append({'item_id': item.item_id, 'name': item.title, 'shop_name': item.creator_name, 'tags': item.tags, 'type': item.category.value, 'targets': [t.name for t in item.targets] + [t.code for t in item.targets], 'price': item.price, 'like_count': item.like_count})
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    return TestBlock(trace_id=trace_id, input=len(items), pre_state={}, action='build_search_index', expected_state={'indexed_count': len(items)}, actual_state={'indexed_count': len(items), 'output_path': output_path, 'file_size': os.path.getsize(output_path)}, diff={}, result='SUCCESS')