import os
import re
import yaml
import unicodedata


def cleanup_ontology():
    ontology_dir = "ontology"
    avatars_path = os.path.join(ontology_dir, "avatars.yaml")
    tags_path = os.path.join(ontology_dir, "tags.yaml")

    # 1. Load avatar terms
    avatar_terms = set()
    if os.path.exists(avatars_path):
        with open(avatars_path, "r", encoding="utf-8") as f:
            avatars = yaml.safe_load(f)
        for key, val in avatars.get("avatars", {}).items():
            avatar_terms.add(key.lower())
            if isinstance(val, dict):
                avatar_terms.add(val.get("canonical_name", "").lower())
                for alias in val.get("aliases", []):
                    avatar_terms.add(str(alias).lower())

    print(f"Loaded {len(avatar_terms)} avatar terms for filtering.")

    # 2. Define generic/low-quality terms to exclude
    GENERIC_EXCLUSIONS = {
        "3dモデル",
        "3d",
        "３d",
        "３dモデル",
        "オリジナル3d",
        "オリジナル３d",
        "オリジナル3dモデル",
        "オリジナル３dモデル",
        "オリジナル3dアバター",
        "オリジナル３dアバター",
        "vrchat",
        "vrc",
        "booth",
        "対応",
        "用",
        "専",
        "avatar",
        "avatars",
        "アバター",
        "3d衣装モデル",
        "3d衣装対応",
        "オリジナル３ｄモデル",
    }

    # Match numeric patterns: e.g. "3アバター", "13アバター", "6 アバター", "VRC想定/17アバター", "28点", "10体"
    BAD_TAG_PATTERN = re.compile(
        r"(?<![a-zA-Z0-9])([0-9]+)\s*(アバター|avatars|avatar|人|モデル|対応|体|点|種類|色|color|colors|way|着|px|shard|avaters|v|av|men\s*avatars|パターン|種|円|%|percent|時間)",
        re.I,
    )

    PLURAL_BAD_PATTERN = re.compile(
        r"^(複数|全|多|多数)\s*(アバター|avatar|avatars|想定|人|体|種類|対応|モデル|キャラクター|shop|ショップ)?$",
        re.I,
    )

    # Helper to check if a key should be excluded
    def should_exclude(key):
        norm_key = unicodedata.normalize("NFKC", str(key))
        kl = norm_key.lower().strip()

        if not kl or len(kl) < 2:
            return True
        if kl in GENERIC_EXCLUSIONS:
            return True
        if re.match(r"^全?\d+$", kl):
            return True
        if BAD_TAG_PATTERN.search(kl):
            return True
        if PLURAL_BAD_PATTERN.match(kl):
            return True

        # Check if it contains or is contained in any avatar name/alias exactly
        for av in avatar_terms:
            if av and (av == kl or av in kl or kl in av):
                return True
        return False

    # 3. Load and clean tags.yaml
    if os.path.exists(tags_path):
        with open(tags_path, "r", encoding="utf-8") as f:
            tags_data = yaml.safe_load(f)

        cleaned_tags = {}
        for section, items in tags_data.items():
            if isinstance(items, dict):
                cleaned_items = {}
                removed_count = 0
                for k, v in items.items():
                    if should_exclude(k):
                        removed_count += 1
                        continue
                    cleaned_items[k] = v
                cleaned_tags[section] = cleaned_items
                print(
                    f"Section [{section}]: Removed {removed_count} low-quality/avatar/numeric tags. Remaining: {len(cleaned_items)}"
                )
            else:
                cleaned_tags[section] = items

        # Save back
        with open(tags_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(cleaned_tags, f, allow_unicode=True, sort_keys=False)
        print("Successfully cleaned tags.yaml!")


if __name__ == "__main__":
    cleanup_ontology()
