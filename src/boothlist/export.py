import logging
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from .normalize import AvatarRef, FileAsset, Item, Variant

logger = logging.getLogger(__name__)


class CatalogExporter:
    def export_catalog(self, items: list[Item], output_path: str = "catalog.yml") -> bool:
        catalog_data = {"items": []}
        for item in items:
            item_dict = {
                "item_id": item.item_id,
                "type": item.type,
                "name": item.name,
                "shop_name": item.shop_name,
                "creator_id": item.creator_id,
                "image_url": item.image_url,
                "url": item.url,
                "current_price": item.current_price,
                "description_excerpt": item.description_excerpt,
                "files": [self._file_asset_to_dict(f) for f in item.files],
                "targets": [self._avatar_ref_to_dict(t) for t in item.targets],
                "tags": item.tags,
                "updated_at": item.updated_at,
            }
            if item.variants:
                item_dict["variants"] = [self._variant_to_dict(v) for v in item.variants]
            catalog_data["items"].append(item_dict)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                catalog_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )
        return True

    def export_metrics(self, items: list[Item], output_path: str = "metrics.yml") -> bool:
        metrics_data = self._generate_metrics(items)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                metrics_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False
            )
        return True

    def _generate_metrics(self, items: list[Item]) -> dict[str, Any]:
        metrics = {
            "summary": {},
            "rankings": {
                "avatar_costume_combinations": [],
                "popular_shops": [],
                "popular_avatars": [],
                "type_distribution": [],
            },
        }
        total_items = len(items)
        total_variants = sum(len(item.variants) for item in items)
        type_counts = Counter(item.type for item in items)
        shop_counts = Counter(item.shop_name for item in items if item.shop_name)
        avatar_counts = defaultdict(int)
        for item in items:
            for target in item.targets:
                avatar_counts[target.code] += 1
            for variant in item.variants:
                for target in variant.targets:
                    avatar_counts[target.code] += 1
        prices = [
            item.current_price
            for item in items
            if item.current_price is not None and item.current_price > 0
        ]
        free_items = [
            item for item in items if item.current_price is not None and item.current_price == 0
        ]
        unknown_price_items = [item for item in items if item.current_price is None]
        metrics["summary"] = {
            "items_total": total_items,
            "variants_total": total_variants,
            "shops_total": len(shop_counts),
            "avatars_supported": len(avatar_counts),
            "price_stats": {
                "total_value": sum(prices) if prices else 0,
                "average_price": round(statistics.mean(prices)) if prices else 0,
                "median_price": round(statistics.median(prices)) if prices else 0,
                "min_price": min(prices) if prices else 0,
                "max_price": max(prices) if prices else 0,
                "priced_items": len(prices),
                "free_items_count": len(free_items),
                "unknown_price_items": len(unknown_price_items),
            },
        }
        metrics["rankings"]["type_distribution"] = [
            {"type": t, "count": c} for t, c in type_counts.most_common()
        ]
        metrics["rankings"]["popular_shops"] = [
            {"shop_name": s, "count": c} for s, c in shop_counts.most_common(10)
        ]
        metrics["rankings"]["popular_avatars"] = [
            {"avatar_code": a, "count": c}
            for a, c in sorted(avatar_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        metrics["rankings"]["avatar_costume_combinations"] = (
            self._calculate_avatar_costume_combinations(items)
        )
        return metrics

    def _calculate_avatar_costume_combinations(self, items: list[Item]) -> list[dict[str, Any]]:
        avatar_items_by_code = defaultdict(list)
        for item in items:
            if item.type == "avatar":
                for target in item.targets:
                    avatar_items_by_code[target.code].append(item)
        costume_combinations = defaultdict(
            lambda: {"count": 0, "prices": [], "avatar_name": None, "costume_name": None}
        )
        for item in items:
            if item.type == "costume":
                for target in item.targets:
                    matching_avatars = avatar_items_by_code.get(target.code, [])
                    if matching_avatars:
                        avatar_item = matching_avatars[0]
                        combo_key = (avatar_item.item_id, item.item_id)
                        combo_data = costume_combinations[combo_key]
                        combo_data["count"] += 1
                        combo_data["avatar_name"] = avatar_item.name
                        combo_data["costume_name"] = item.name
                        if item.current_price is not None:
                            combo_data["prices"].append(item.current_price)
                    else:
                        combo_key = (f"avatar_{target.code}", item.item_id)
                        combo_data = costume_combinations[combo_key]
                        combo_data["count"] += 1
                        combo_data["avatar_name"] = target.name
                        combo_data["costume_name"] = item.name
                        if item.current_price is not None:
                            combo_data["prices"].append(item.current_price)
        combinations = []
        for (avatar_item_id, costume_item_id), data in costume_combinations.items():
            prices = data["prices"]
            combo = {
                "avatar_item_id": avatar_item_id,
                "costume_item_id": costume_item_id,
                "avatar_name": data["avatar_name"],
                "costume_name": data["costume_name"],
                "count": data["count"],
                "total_price": sum(prices) if prices else 0,
                "avg_price": round(statistics.mean(prices)) if prices else 0,
                "median_price": round(statistics.median(prices)) if prices else 0,
            }
            combinations.append(combo)
        combinations.sort(key=lambda x: x["count"], reverse=True)
        return combinations[:20]

    def _file_asset_to_dict(self, file_asset: FileAsset) -> dict[str, Any]:
        return {
            "filename": file_asset.filename,
            "version": file_asset.version,
            "size": file_asset.size,
            "hash": file_asset.hash,
        }

    def _avatar_ref_to_dict(self, avatar_ref: AvatarRef) -> dict[str, Any]:
        return {"code": avatar_ref.code, "name": avatar_ref.name}

    def _variant_to_dict(self, variant: Variant) -> dict[str, Any]:
        return {
            "subitem_id": variant.subitem_id,
            "parent_item_id": variant.parent_item_id,
            "variant_name": variant.variant_name,
            "targets": [self._avatar_ref_to_dict(t) for t in variant.targets],
            "files": [self._file_asset_to_dict(f) for f in variant.files],
            "notes": variant.notes,
        }


class HTMLDashboardExporter:
    def export_dashboard(self, output_path: str = "index.html") -> bool:
        html_content = self._generate_html_template()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return True

    def _generate_html_template(self) -> str:
        template_path = Path("index.html")
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        return "index.html template not found."

