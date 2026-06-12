import json
import os

from .core import Message, TestBlock


def validate_search_index(block: TestBlock) -> Message:
    output_paths = block.actual_state.get("output_paths", ["api/search_index_part0.json"])
    
    indexed_count = 0
    missing_files = []
    is_valid_json = True
    
    for output_path in output_paths:
        if not os.path.exists(output_path):
            missing_files.append(output_path)
            continue
            
        try:
            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    is_valid_json = False
                indexed_count += len(data)
        except Exception:
            is_valid_json = False
            
    expected_count = block.expected_state.get("indexed_count", 0)
    file_exists = len(missing_files) == 0
    status = (
        "SUCCESS"
        if file_exists and is_valid_json and (indexed_count == expected_count)
        else "WARNING"
    )
    payload = {
        "status": status,
        "file_exists": file_exists,
        "is_valid_json": is_valid_json,
        "expected_count": expected_count,
        "actual_count": indexed_count,
        "details": f"Verified {indexed_count} entries across {len(output_paths)} shards. Missing: {missing_files}",
    }
    return Message(
        from_agent="search_validator",
        to_agent="main_agent",
        trace_id=block.trace_id,
        payload=payload,
    )
