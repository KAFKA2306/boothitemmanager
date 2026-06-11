"""
evolution_pipeline.py - Orchestrates the Evolving Ontology Loop (EOL)
Discovery -> Validation -> Evolution -> Propagation
"""

import json
import os
from datetime import datetime

import yaml
from jsonschema import ValidationError, validate

# Path Configuration
ONTOLOGY_DIR = "ontology"
AVATARS_PATH = os.path.join(ONTOLOGY_DIR, "avatars.yaml")
TAGS_PATH = os.path.join(ONTOLOGY_DIR, "tags.yaml")
STYLES_PATH = os.path.join(ONTOLOGY_DIR, "styles.yaml")
SCHEMA_PATH = os.path.join(ONTOLOGY_DIR, "schema.json")
LOG_PATH = os.path.join(ONTOLOGY_DIR, "evolution_log.json")
CATALOG_PATH = "data/structured/catalog.json"


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def log_evolution(event_type, description):
    log = []
    if os.path.exists(LOG_PATH):
        log = load_json(LOG_PATH)

    log.append(
        {"timestamp": datetime.now().isoformat(), "event": event_type, "description": description}
    )

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)



def _is_untagged(item):
    tag_set = item.get("tag_set", {})
    if not tag_set.get("style") or not tag_set.get("color"):
        return item.get("item_id")
    return None

# キャッシュ用変数
_VALID_TAGS = None

def _get_valid_tags():
    global _VALID_TAGS
    if _VALID_TAGS is None:
        tags = load_yaml(TAGS_PATH)
        color_map = {}
        for k, v in tags.get("Colors", {}).items():
            color_map[k.lower()] = k
            for alias in v.get("aliases", []):
                color_map[alias.lower()] = k
        style_map = {}
        for k, v in tags.get("Styles", {}).items():
            style_map[k.lower()] = k
            for alias in v.get("aliases", []):
                style_map[alias.lower()] = k
        _VALID_TAGS = {"color": color_map, "style": style_map}
    return _VALID_TAGS

def generate_tags(item):
    tags_data = _get_valid_tags()
    current_tags = item.get("tag_set", {})
    
    def normalize(val, map_dict):
        return map_dict.get(val.lower(), "Other")

    new_style = [normalize(s, tags_data["style"]) for s in current_tags.get("style", [])]
    new_color = [normalize(c, tags_data["color"]) for c in current_tags.get("color", [])]
    
    item["tag_set"] = {
        "style": list(set(new_style)) if new_style else ["Other"],
        "color": list(set(new_color)) if new_color else ["Other"],
        "accessory": current_tags.get("accessory", ["none"]),
        "appearance": current_tags.get("appearance", ["standard"])
    }
    return item


def discovery_phase():
    print("🔍 [EOL:DISCOVERY] Analyzing dataset for missing tags...")
    catalog = load_json(CATALOG_PATH)
    
    needs_update = False
    for item in catalog:
        if _is_untagged(item):
            print(f"🛠️ [EOL:DISCOVERY] Generating tags for {item.get('item_id')}")
            generate_tags(item)
            needs_update = True
            
    if needs_update:
        with open(CATALOG_PATH, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        print("✅ [EOL:DISCOVERY] Tags generated and catalog updated.")
    else:
        print("✅ [EOL:DISCOVERY] All items have tags.")


def validation_phase():
    print(json.dumps({"event": "validation_start", "description": "Enforcing API Schema Contract and Quality Gateway"}))
    schema = load_json(SCHEMA_PATH)
    catalog = load_json(CATALOG_PATH)

    for item in catalog:
        tag_set = item.get("tag_set", {})
        if not tag_set.get("style") or not tag_set.get("color"):
            raise ValueError(json.dumps({"event": "quality_gate_rejected", "item_id": item.get("item_id")}))

        try:
            validate_item = {
                "item_id": str(item.get("item_id")),
                "title": item.get("title"),
                "category": item.get("category"),
                "price": item.get("price"),
                "compatible_avatars": [
                    (t.get("code") or t.get("name") or str(t)) if isinstance(t, dict) else str(t)
                    for t in (item.get("targets") or [])
                ],
                "tags": item.get("tags_raw") if item.get("tags_raw") is not None else [],
                "thumbnail": item.get("thumbnail_url"),
                "booth_url": item.get("source_url"),
                "author": item.get("creator_name"),
                "description": item.get("description", ""),
                "published_at": item.get("published_at"),
                "like_count": item.get("like_count", 0)
            }
            tag_set = item.get("tag_set", {})
            for k in ["style", "color", "accessory", "appearance"]:
                if k in tag_set:
                    validate_item[k] = tag_set[k]

            validate(instance=validate_item, schema=schema)
        except ValidationError as e:
            print(json.dumps({"event": "schema_violation", "item_id": item.get("item_id"), "error": str(e)}))
            raise e


def evolution_phase():
    print(json.dumps({"event": "evolution_start", "description": "Applying Ontology updates"}))
    avatars = load_yaml(AVATARS_PATH)

    for code, data in avatars.get("avatars", {}).items():
        assert "booth_item_id" in data, json.dumps({"event": "evolution_error", "reason": f"Missing item_id for avatar: {code}"})
        assert data.get("confidence", 0) >= 0.0, json.dumps({"event": "evolution_error", "reason": f"Invalid confidence for: {code}"})


def propagation_phase():
    print(json.dumps({"event": "propagation_start", "description": "Syncing changes to Static API"}))
    res = os.system("python3 run_bulk_pipeline.py")
    if res != 0:
        raise RuntimeError(json.dumps({"event": "propagation_failed", "exit_code": res}))


def main():
    print(json.dumps({"event": "pipeline_start", "description": "Initializing Autonomous Evolution Loop (Zero-Trust Mode)"}))
    try:
        discovery_phase()
        validation_phase()
        evolution_phase()
        propagation_phase()
    except Exception as e:
        print(json.dumps({"event": "pipeline_failed", "error": str(e)}))
        raise e

    log_evolution(
        "pipeline_run_verified", "Autonomous cycle completed with full schema enforcement."
    )
    print(json.dumps({"event": "pipeline_complete", "description": "Cycle Complete. Axiomatic Space remains consistent."}))


if __name__ == "__main__":
    main()
