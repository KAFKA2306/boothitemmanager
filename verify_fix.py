
import sys
import os
import re
from datetime import datetime

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from boothitemmanager2.agents.normalizer import _infer_item_type, _pick_targets, _load_aliases
from boothitemmanager2.schemas.storage import RawAssetPage, ItemType
from bs4 import BeautifulSoup

def test_item(item_id):
    file_path = f'input/raw/{item_id}.html'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')
    
    # Simple extraction for testing
    from boothitemmanager2.agents.normalizer import _pick_name, _pick_description, _pick_tags, _parse_og_tags
    og_data = _parse_og_tags(soup)
    name = _pick_name(soup, og_data)
    description = _pick_description(soup, og_data)
    tags = _pick_tags(soup)
    aliases = _load_aliases()
    
    targets = _pick_targets(name, description, tags, aliases)
    
    # Debug _infer_item_type
    full_text = f"{name} {description or ''} {' '.join(tags)}".lower()
    types_map = aliases.get('types', {})
    
    print(f"Item ID: {item_id}")
    print(f"Name: {name}")
    
    # Step 1 check
    if len(targets) > 1:
        acc_aliases = types_map.get('accessory', {}).get('aliases', [])
        for term in acc_aliases:
            if term.lower() in full_text:
                print(f"DEBUG: Matched accessory alias in Step 1: {term}")
    
    item_type = _infer_item_type(name, description, tags, targets, aliases)
    print(f"Type: {item_type}")
    print(f"Targets: {[t.name for t in item.targets] if 'item' in locals() else [t.name for t in targets]}")
    print("-" * 20)

if __name__ == "__main__":
    for item_id in [4281941, 4837941, 4414941]:
        test_item(item_id)
