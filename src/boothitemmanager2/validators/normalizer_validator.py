from ..core import TestBlock, Message
from ..schemas.storage import Item

def validate_normalization(block: TestBlock) -> Message:
    """
    Validates the result of Normalizer Agent with high-strictness for Audit.
    Zero-Fat: Focused on field presence and data quality.
    """
    actual = block.actual_state
    item = actual.get("item")
    
    is_valid = False
    reasons = []
    observations = []
    
    if isinstance(item, Item):
        observations.append(f"Item object found: {item.item_id}")
        
        # Identity Checks
        if not item.shop_name or item.shop_name == "Unknown Shop":
            reasons.append("shop_name is missing or 'Unknown Shop'")
        
        if not item.creator_id or item.creator_id == "unknown":
            reasons.append("creator_id is missing or 'unknown'")

        # Feature Completeness Checks
        if not item.tags:
            observations.append("Warning: tags list is empty")
        
        if not item.files:
            observations.append("Warning: files list is empty")
            
        if not item.targets:
            observations.append("Warning: targets (AvatarRef) is empty")
            
        # Basic required fields
        if not item.name: reasons.append("name is missing")
        if not item.type: reasons.append("type is missing")
        if not item.image_url: reasons.append("image_url is missing")
        
        if not reasons:
            is_valid = True
            observations.append("All critical fields and identity info are present.")
        else:
            observations.append(f"Validation failed: {', '.join(reasons)}")
            
        observations.append(f"Inferred type: {item.type}")
        observations.append(f"Tags found: {len(item.tags)}")
        observations.append(f"Files found: {len(item.files)}")
        observations.append(f"Targets found: {len(item.targets)}")
            
    else:
        observations.append("Item object is missing from actual_state.")
        reasons.append("Item object missing")

    payload = {
        "status": "VALID" if is_valid else "INVALID",
        "reasons": reasons,
        "observations": observations,
        "item_summary": {
            "item_id": item.item_id if item else None,
            "name": item.name if item else None,
            "type": item.type if item else None,
            "shop_name": item.shop_name if item else None,
            "creator_id": item.creator_id if item else None
        } if item else None
    }

    return Message(
        from_agent="normalizer_validator",
        to_agent="main_agent",
        trace_id=block.trace_id,
        payload=payload
    )
