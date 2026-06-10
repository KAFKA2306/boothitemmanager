from ..core import TestBlock, Message
from ..schemas.storage import RawAssetPage

def validate_crawl(block: TestBlock) -> Message:
    """
    Validates the result of Crawler Agent and reports to the main agent.
    Constraint: No REJECT authority. Just observation and reporting.
    Zero-Fat: Minimal validation logic.
    """
    actual = block.actual_state
    raw_page = actual.get("raw_page")
    
    is_valid = False
    observations = []
    
    if isinstance(raw_page, RawAssetPage):
        if len(raw_page.content) > 0:
            observations.append("RawAssetPage captured successfully.")
            if actual.get("saved"):
                observations.append(f"Raw data accumulated at {actual.get('save_path')}.")
                is_valid = True
            else:
                observations.append("Raw data accumulation failed.")
        else:
            observations.append("RawAssetPage captured but content is empty.")
    else:
        observations.append("RawAssetPage is missing from actual_state.")

    payload = {
        "status": "VALID" if is_valid else "INVALID",
        "observations": observations,
        "metrics": {
            "status_code": actual.get("status_code"),
            "content_length": actual.get("content_length")
        }
    }

    return Message(
        from_agent="crawler_validator",
        to_agent="main_agent",
        trace_id=block.trace_id,
        payload=payload
    )
