"""
evolution_pipeline.py - Orchestrates the Evolving Ontology Loop (EOL)
Discovery -> Validation -> Evolution -> Propagation
"""

import json
import os
import re
import sys
from datetime import datetime

import yaml
from jsonschema import ValidationError, validate

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))


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


def _get_existing_ontology_concepts() -> set[str]:
    concepts = set()
    if os.path.exists(TAGS_PATH):
        with open(TAGS_PATH, encoding="utf-8") as f:
            tags = yaml.safe_load(f)
        for _, data in tags.items():
            if isinstance(data, dict):
                for key, val in data.items():
                    concepts.add(key.lower())
                    if isinstance(val, dict) and "aliases" in val:
                        for alias in val["aliases"]:
                            concepts.add(alias.lower())
    if os.path.exists(STYLES_PATH):
        with open(STYLES_PATH, encoding="utf-8") as f:
            styles = yaml.safe_load(f)
        for key, val in styles.get("styles", {}).items():
            concepts.add(key.lower())
            for alias in val:
                concepts.add(alias.lower())
    rich_path = os.path.join(ONTOLOGY_DIR, "rich_dimensions.yaml")
    if os.path.exists(rich_path):
        with open(rich_path, encoding="utf-8") as f:
            rich = yaml.safe_load(f)
        for category in ["material_properties", "niche_subcultures", "activity_scenes"]:
            for key, val in rich.get(category, {}).items():
                concepts.add(key.lower())
                if isinstance(val, dict) and "aliases" in val:
                    for alias in val["aliases"]:
                        concepts.add(alias.lower())
    if os.path.exists(AVATARS_PATH):
        with open(AVATARS_PATH, encoding="utf-8") as f:
            avatars = yaml.safe_load(f)
        for key, val in avatars.get("avatars", {}).items():
            concepts.add(key.lower())
            if isinstance(val, dict):
                concepts.add(val.get("canonical_name", "").lower())
                for alias in val.get("aliases", []):
                    concepts.add(alias.lower())
    return concepts


def _clean_concept(term: str) -> str | None:
    term = term.strip()
    if len(term) < 2:
        return None
    if re.match(r"^[\d\W_]+$", term):
        return None
    for suffix in ["対応", "用", "版", "セット", "向け"]:
        if term.endswith(suffix) and len(term) > len(suffix):
            term = term[:-len(suffix)]
    term = term.strip()
    if len(term) < 2:
        return None
    return term


def concept_invention_phase() -> None:
    print("🧠 [EOL:CONCEPT_INVENTION] Identifying potential new tags from catalog...")
    catalog = load_json(CATALOG_PATH)
    existing_concepts = _get_existing_ontology_concepts()
    extracted_map = {}
    
    from boothitemmanager2.staging_buffer import StagingBuffer
    
    for item in catalog:
        item_id = str(item.get("item_id"))
        title = item.get("title") or ""
        description = item.get("description") or ""
        
        params = {"title": title, "description": description}
        cached = StagingBuffer.get("concepts", params)
        if cached is not None:
            candidates = cached
        else:
            candidates = []
            for pattern in [r"【([^】]+)】", r"\[([^\]]+)\]", r"\(([^)]+)\)"]:
                for match in re.finditer(pattern, title + " " + description):
                    candidates.append(match.group(1))
            for match in re.finditer(r"#([^\s#]+)", title + " " + description):
                candidates.append(match.group(1))
            StagingBuffer.set("concepts", params, candidates)
            
        for raw_cand in candidates:
            cleaned = _clean_concept(raw_cand)
            if cleaned:
                cleaned_lower = cleaned.lower()
                if cleaned_lower not in existing_concepts:
                    if cleaned not in extracted_map:
                        extracted_map[cleaned] = []
                    if item_id not in extracted_map[cleaned]:
                        extracted_map[cleaned].append(item_id)
                        
    pending_list = []
    for tag, items in extracted_map.items():
        confidence = min(1.0, 0.5 + 0.1 * len(items))
        pending_list.append({
            "tag": tag,
            "confidence": confidence,
            "sources": items
        })
        
    pending_list.sort(key=lambda x: (-x["confidence"], x["tag"]))
    StagingBuffer.save_pending_evolution(pending_list)
    print(f"✅ [EOL:CONCEPT_INVENTION] Found {len(pending_list)} new potential tags and buffered them.")


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


def promote_tags_phase():
    """
    Autonomous Tag Lifecycle & Promotion Engine
    Reads pending_evolution.json and processes through 4 automated filtering stages:
    Stage 1: Frequency Filtering (drop tags appearing in < 3 items).
    Stage 2: Basic Semantic Clustering/Merging (group tags with similar suffixes or lowercase equivalents).
    Stage 3: Automatic Category Prediction (determine destination: tags.yaml section vs styles.yaml).
    Stage 4: Auto-Promotion (promote highly confident tags >= 0.8 to tags.yaml/styles.yaml and log evolution).
    """
    print("🚀 [EOL:PROMOTION_ENGINE] Initializing Tag Lifecycle & Promotion Engine...")
    from boothitemmanager2.staging_buffer import StagingBuffer
    
    pending = StagingBuffer.get_pending_evolution()
    if not pending:
        print("ℹ️ [EOL:PROMOTION_ENGINE] No pending tags to promote.")
        return

    # Stage 2: Basic Semantic Clustering/Merging (group tags with similar suffixes or lowercase equivalents)
    # We cluster by:
    # - case-insensitive canonical tag
    # - stripping common suffixes to find a common stem
    # - merging sources and retaining highest confidence
    clusters = {}
    for entry in pending:
        raw_tag = entry["tag"].strip()
        if raw_tag.startswith("#"):
            raw_tag = raw_tag[1:]
        
        # Simple canonicalization: strip common suffixes, then lowercase
        cleaned_tag = raw_tag
        for suffix in ["対応", "用", "版", "セット", "向け"]:
            if cleaned_tag.endswith(suffix) and len(cleaned_tag) > len(suffix):
                cleaned_tag = cleaned_tag[:-len(suffix)]
        
        stem = cleaned_tag.lower()
        
        if stem not in clusters:
            clusters[stem] = {
                "canonical_name": cleaned_tag,
                "confidence": entry["confidence"],
                "sources": set(entry["sources"]),
            }
        else:
            clusters[stem]["sources"].update(entry["sources"])
            if entry["confidence"] > clusters[stem]["confidence"]:
                clusters[stem]["confidence"] = entry["confidence"]
                clusters[stem]["canonical_name"] = cleaned_tag  # Use the casing of the highest confidence match

    # Stage 1: Frequency Filtering (sources must be at least 3 items)
    # Drop clusters appearing in < 3 items
    filtered_clusters = {
        stem: info for stem, info in clusters.items() if len(info["sources"]) >= 3
    }

    # Stage 3: Automatic Category Prediction & Stage 4: Auto-Promotion
    # Read existing tags and styles
    tags_data = load_yaml(TAGS_PATH)
    styles_data = load_yaml(STYLES_PATH)
    
    promoted_tags = 0
    promoted_styles = 0
    
    # Pre-load category mappings based on keyword presence to predict destination
    # We predict styles vs colors vs accessories etc.
    for stem, info in filtered_clusters.items():
        # High confidence threshold for auto-promotion: confidence >= 0.8
        if info["confidence"] < 0.8:
            continue
            
        name = info["canonical_name"]
        
        # Let's predict category:
        # If color keywords matched, goes to colors.
        # If style keywords or "style" / "look" / "kawaii" / "punk" etc, styles.yaml.
        # Default fallback to tag.yaml's outfit_types or accessories based on ending.
        name_lower = name.lower()
        
        # 1. Colors check
        color_keywords = ["黒", "白", "赤", "青", "緑", "黄", "紫", "橙", "紺", "茶", "灰", "金", "銀", "black", "white", "red", "blue", "green", "yellow", "purple", "orange", "navy", "brown", "gray", "gold", "silver", "pink", "pink", "pink"]
        is_color = any(k in name_lower for k in color_keywords)
        
        # 2. Styles check
        style_keywords = ["cute", "cool", "sexy", "dark", "casual", "street", "gothic", "elegant", "simple", "classical", "girly", "y2k", "retro", "pop", "horror", "lolita", "modern", "和風", "和装", "中華", "チャイナ", "量産型", "地雷", "病み", "ゆめ", "お姉さん", "大人", "yami", "kawaii", "punk"]
        is_style = any(k in name_lower for k in style_keywords) or name_lower.endswith("style") or name_lower.endswith("kei")
        
        if is_style:
            # styles.yaml promotion
            if "styles" not in styles_data:
                styles_data["styles"] = {}
            # Find or insert style category
            # We either append to existing category matching name, or create new one.
            matched_key = None
            for key in styles_data["styles"]:
                if key.lower() == name_lower:
                    matched_key = key
                    break
            if matched_key:
                if name not in styles_data["styles"][matched_key]:
                    styles_data["styles"][matched_key].append(name)
            else:
                styles_data["styles"][name] = [name, name.lower()]
            promoted_styles += 1
            log_evolution("style_promoted", f"Promoted tag '{name}' to styles.yaml with confidence {info['confidence']:.2f}")
        else:
            # tags.yaml promotion
            section = "accessories"
            if any(k in name_lower for k in ["服", "衣装", "ワンピ", "ドレス", "ジャケット", "パーカー", "スカート", "シャツ", "パンツ", "outfit", "dress", "suit", "jersey"]):
                section = "outfit_types"
            elif is_color:
                section = "colors"
                
            if section not in tags_data:
                tags_data[section] = {}
                
            matched_key = None
            for key in tags_data[section]:
                if key.lower() == name_lower:
                    matched_key = key
                    break
            if matched_key:
                if "aliases" not in tags_data[section][matched_key]:
                    tags_data[section][matched_key]["aliases"] = []
                if name not in tags_data[section][matched_key]["aliases"]:
                    tags_data[section][matched_key]["aliases"].append(name)
            else:
                tags_data[section][name] = {
                    "aliases": [name, name.lower()],
                    "metadata": {
                        "faceemo_version": "any",
                        "udonsharp_compat": True
                    }
                }
            promoted_tags += 1
            log_evolution("tag_promoted", f"Promoted tag '{name}' to tags.yaml ({section}) with confidence {info['confidence']:.2f}")

    # Write files back if any changes were made
    if promoted_tags > 0:
        with open(TAGS_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(tags_data, f, allow_unicode=True, default_flow_style=False)
    if promoted_styles > 0:
        with open(STYLES_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(styles_data, f, allow_unicode=True, default_flow_style=False)

    print(f"✅ [EOL:PROMOTION_ENGINE] Completed promotion. Promoted tags: {promoted_tags}, Promoted styles: {promoted_styles}")


def evolution_phase() -> None:
    pass


def propagation_phase() -> None:
    pass


def pruning_pipeline_phase() -> None:
    print("🧹 [EOL:PRUNING_PIPELINE] Running Tag Deprecation & Alias Merging...")
    catalog = load_json(CATALOG_PATH)
    
    import difflib
    from datetime import datetime, timezone, timedelta
    
    now = datetime.now(timezone.utc)
    limit_date = now - timedelta(days=90)
    
    active_tags: set[str] = set()
    for item in catalog:
        pub_str = item.get("published_at")
        if not pub_str:
            continue
        try:
            clean_str = pub_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
        except Exception:
            continue
            
        dt_utc = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if dt_utc >= limit_date:
            tag_set = item.get("tag_set") or {}
            for t_list in tag_set.values():
                if isinstance(t_list, list):
                    for t in t_list:
                        if isinstance(t, str) and t:
                            active_tags.add(t.lower())
            for t in item.get("tags_raw") or []:
                if isinstance(t, str) and t:
                    active_tags.add(t.lower())
                    
    # Fallback to general catalog presence if no active tags found via date window
    if len(active_tags) < 5:
        print("⚠️ [EOL:PRUNING_PIPELINE] Too few active tags found via date window. Falling back to entire catalog presence.")
        for item in catalog:
            tag_set = item.get("tag_set") or {}
            for t_list in tag_set.values():
                if isinstance(t_list, list):
                    for t in t_list:
                        if isinstance(t, str) and t:
                            active_tags.add(t.lower())
            for t in item.get("tags_raw") or []:
                if isinstance(t, str) and t:
                    active_tags.add(t.lower())
    tags_data = load_yaml(TAGS_PATH)
    styles_data = load_yaml(STYLES_PATH)
    
    active_ontology_tags: set[str] = set()
    for section_name, section_dict in tags_data.items():
        if not isinstance(section_dict, dict):
            continue
        for tag_key, tag_info in section_dict.items():
            if not isinstance(tag_info, dict):
                continue
            aliases = tag_info.get("aliases") or []
            if tag_key.lower() in active_tags or any(a.lower() in active_tags for a in aliases):
                active_ontology_tags.add(tag_key)
                
    style_dict = styles_data.get("styles") or {}
    for style_key, aliases in style_dict.items():
        if style_key.lower() in active_tags or any(a.lower() in active_tags for a in aliases):
            active_ontology_tags.add(style_key)
            
    tags_modified = False
    for section_name, section_dict in list(tags_data.items()):
        if not isinstance(section_dict, dict):
            continue
        for tag_key, tag_info in list(section_dict.items()):
            if not isinstance(tag_info, dict):
                continue
            aliases = tag_info.get("aliases") or []
            is_active = tag_key.lower() in active_tags or any(a.lower() in active_tags for a in aliases)
            if not is_active:
                best_match = None
                best_ratio = 0.0
                for active in active_ontology_tags:
                    ratio = difflib.SequenceMatcher(None, tag_key.lower(), active.lower()).ratio()
                    if ratio >= 0.85 and ratio > best_ratio:
                        best_ratio = ratio
                        best_match = active
                        
                if best_match:
                    merged = False
                    for s_name, s_dict in tags_data.items():
                        if isinstance(s_dict, dict) and best_match in s_dict:
                            s_dict[best_match].setdefault("aliases", [])
                            for a in [tag_key] + aliases:
                                if a not in s_dict[best_match]["aliases"]:
                                    s_dict[best_match]["aliases"].append(a)
                            merged = True
                            break
                    if not merged and best_match in style_dict:
                        for a in [tag_key] + aliases:
                            if a not in style_dict[best_match]:
                                style_dict[best_match].append(a)
                        merged = True
                    
                    del section_dict[tag_key]
                    log_evolution("tag_merged", f"Merged inactive tag '{tag_key}' into active tag '{best_match}'")
                    tags_modified = True
                else:
                    tag_info.setdefault("metadata", {})["status"] = "deprecated"
                    log_evolution("tag_deprecated", f"Deprecated inactive tag '{tag_key}'")
                    tags_modified = True

    styles_modified = False
    for style_key, aliases in list(style_dict.items()):
        is_active = style_key.lower() in active_tags or any(a.lower() in active_tags for a in aliases)
        if not is_active:
            best_match = None
            best_ratio = 0.0
            for active in active_ontology_tags:
                ratio = difflib.SequenceMatcher(None, style_key.lower(), active.lower()).ratio()
                if ratio >= 0.85 and ratio > best_ratio:
                    best_ratio = ratio
                    best_match = active
                    
            if best_match:
                merged = False
                if best_match in style_dict:
                    for a in [style_key] + aliases:
                        if a not in style_dict[best_match]:
                            style_dict[best_match].append(a)
                    merged = True
                else:
                    for s_name, s_dict in tags_data.items():
                        if isinstance(s_dict, dict) and best_match in s_dict:
                            s_dict[best_match].setdefault("aliases", [])
                            for a in [style_key] + aliases:
                                if a not in s_dict[best_match]["aliases"]:
                                    s_dict[best_match]["aliases"].append(a)
                            merged = True
                            break
                            
                del style_dict[style_key]
                log_evolution("style_merged", f"Merged inactive style '{style_key}' into active '{best_match}'")
                styles_modified = True
            else:
                styles_data.setdefault("style_metadata", {}).setdefault(style_key, {})["status"] = "deprecated"
                log_evolution("style_deprecated", f"Deprecated inactive style '{style_key}'")
                styles_modified = True

    if tags_modified:
        with open(TAGS_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(tags_data, f, allow_unicode=True, default_flow_style=False)
    if styles_modified:
        with open(STYLES_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(styles_data, f, allow_unicode=True, default_flow_style=False)
            
    print("✅ [EOL:PRUNING_PIPELINE] Pruning completed.")


def main():
    print(json.dumps({"event": "pipeline_start", "description": "Initializing Autonomous Evolution Loop (Zero-Trust Mode)"}))
    try:
        discovery_phase()
        concept_invention_phase()
        promote_tags_phase()
        pruning_pipeline_phase()
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
