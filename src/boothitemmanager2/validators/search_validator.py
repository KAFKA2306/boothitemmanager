import json
import os
from ..core import TestBlock, Message

def validate_search_index(block: TestBlock) -> Message:
    """
    Validates the search index build result.
    Checks file existence and basic structure.
    """
    output_path = block.actual_state.get("output_path", "api/search_index.json")
    
    file_exists = os.path.exists(output_path)
    indexed_count = 0
    is_valid_json = False
    
    if file_exists:
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            indexed_count = len(data)
            is_valid_json = isinstance(data, list)

    expected_count = block.expected_state.get("indexed_count", 0)
    status = "SUCCESS" if file_exists and is_valid_json and indexed_count == expected_count else "WARNING"
    
    payload = {
        "status": status,
        "file_exists": file_exists,
        "is_valid_json": is_valid_json,
        "expected_count": expected_count,
        "actual_count": indexed_count,
        "details": f"Verified {indexed_count} entries in {output_path}"
    }

    return Message(
        from_agent="search_validator",
        to_agent="main_agent",
        trace_id=block.trace_id,
        payload=payload
    )
