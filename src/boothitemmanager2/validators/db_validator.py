import json
import os
from ..core import TestBlock, Message

def validate_db(block: TestBlock) -> Message:
    output_path = block.actual_state.get('output_path', 'data/structured/catalog.json')
    file_exists = os.path.exists(output_path)
    item_count = 0
    if file_exists:
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            item_count = len(data)
    expected_count = block.expected_state.get('item_count', 0)
    status = 'SUCCESS' if file_exists and item_count == expected_count else 'WARNING'
    payload = {'status': status, 'file_exists': file_exists, 'expected_count': expected_count, 'actual_count': item_count, 'details': f'Verified {item_count} items in {output_path}'}
    return Message(from_agent='db_validator', to_agent='main_agent', trace_id=block.trace_id, payload=payload)