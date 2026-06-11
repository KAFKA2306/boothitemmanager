import json
import os

from .core import Message, TestBlock


def validate_api(block: TestBlock) -> Message:
    api_dir = block.actual_state.get("api_dir", "api")
    critical_files = ["catalog.json", "items/all.json", "metrics.json"]
    existence = {f: os.path.exists(os.path.join(api_dir, f)) for f in critical_files}
    all_exist = all(existence.values())
    item_count = block.actual_state.get("item_count", 0)
    metrics_valid = False
    if existence["metrics.json"]:
        with open(os.path.join(api_dir, "metrics.json"), encoding="utf-8") as f:
            metrics = json.load(f)
            metrics_valid = "total_items" in metrics and metrics["total_items"] == item_count
    status = "SUCCESS" if all_exist and metrics_valid else "WARNING"
    payload = {
        "status": status,
        "existence": existence,
        "metrics_valid": metrics_valid,
        "item_count": item_count,
        "details": f"API validation complete for {api_dir}. Status: {status}",
    }
    return Message(
        from_agent="api_validator", to_agent="main_agent", trace_id=block.trace_id, payload=payload
    )
