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
            yaml.dump(catalog_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return True

    def export_metrics(self, items: list[Item], output_path: str = "metrics.yml") -> bool:
        metrics_data = self._generate_metrics(items)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(metrics_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
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
            for target in item.targets: avatar_counts[target.code] += 1
            for variant in item.variants:
                for target in variant.targets: avatar_counts[target.code] += 1

        prices = [item.current_price for item in items if item.current_price is not None and item.current_price > 0]
        free_items = [item for item in items if item.current_price is not None and item.current_price == 0]
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

        metrics["rankings"]["type_distribution"] = [{"type": t, "count": c} for t, c in type_counts.most_common()]
        metrics["rankings"]["popular_shops"] = [{"shop_name": s, "count": c} for s, c in shop_counts.most_common(10)]
        metrics["rankings"]["popular_avatars"] = [{"avatar_code": a, "count": c} for a, c in sorted(avatar_counts.items(), key=lambda x: x[1], reverse=True)]
        metrics["rankings"]["avatar_costume_combinations"] = self._calculate_avatar_costume_combinations(items)
        return metrics

    def _calculate_avatar_costume_combinations(self, items: list[Item]) -> list[dict[str, Any]]:
        avatar_items_by_code = defaultdict(list)
        for item in items:
            if item.type == "avatar":
                for target in item.targets: avatar_items_by_code[target.code].append(item)

        costume_combinations = defaultdict(lambda: {"count": 0, "prices": [], "avatar_name": None, "costume_name": None})

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
                        if item.current_price is not None: combo_data["prices"].append(item.current_price)
                    else:
                        combo_key = (f"avatar_{target.code}", item.item_id)
                        combo_data = costume_combinations[combo_key]
                        combo_data["count"] += 1
                        combo_data["avatar_name"] = target.name
                        combo_data["costume_name"] = item.name
                        if item.current_price is not None: combo_data["prices"].append(item.current_price)

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
        return {"filename": file_asset.filename, "version": file_asset.version, "size": file_asset.size, "hash": file_asset.hash}

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
        return """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BoothList - BOOTH Asset Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
        .search-bar { width: 100%; padding: 12px; font-size: 16px; border: 2px solid #ddd; border-radius: 4px; margin-bottom: 20px; }
        .filters { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .filter { padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; }
        .filter.active { background: #007acc; color: white; }
        .items-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .item-card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: white; transition: box-shadow 0.2s; }
        .item-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
        .item-image { width: 100%; height: 150px; background: #f0f0f0; border-radius: 4px; margin-bottom: 10px; display: flex; align-items: center; justify-content: center; color: #666; }
        .item-title { font-weight: bold; margin-bottom: 5px; color: #333; }
        .item-shop { color: #666; font-size: 14px; margin-bottom: 5px; }
        .item-price { color: #007acc; font-weight: bold; }
        .item-targets { margin-top: 10px; }
        .target-tag { display: inline-block; background: #e7f3ff; color: #007acc; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin: 2px; }
        .loading { text-align: center; padding: 50px; color: #666; }
        .stats { display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; min-width: 120px; }
        .stat-number { font-size: 24px; font-weight: bold; color: #007acc; }
        .stat-label { font-size: 14px; color: #666; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>BoothList - BOOTH Asset Dashboard</h1>
        <div class="stats" id="stats">
            <div class="stat-card"><div class="stat-number" id="total-items">-</div><div class="stat-label">Total Items</div></div>
            <div class="stat-card"><div class="stat-number" id="total-variants">-</div><div class="stat-label">Variants</div></div>
            <div class="stat-card"><div class="stat-number" id="total-shops">-</div><div class="stat-label">Shops</div></div>
            <div class="stat-card"><div class="stat-number" id="total-value">-</div><div class="stat-label">Total Value</div></div>
        </div>
        <input type="text" class="search-bar" id="search" placeholder="Search items, shops, avatars...">
        <div class="filters" id="filters"><div class="filter active" data-type="all">All</div></div>
        <div class="loading" id="loading">Loading catalog...</div>
        <div class="items-grid" id="items" style="display: none;"></div>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/js-yaml/4.1.0/js-yaml.min.js"></script>
    <script>
        let allItems = [], filteredItems = [], activeFilter = 'all';
        async function loadData() {
            try {
                const [cRes, mRes] = await Promise.all([fetch('catalog.yml'), fetch('metrics.yml')]);
                const cYaml = await cRes.text();
                const mYaml = await mRes.text();
                const catalog = jsyaml.load(cYaml);
                const metrics = jsyaml.load(mYaml);
                allItems = catalog.items || [];
                updateStats(metrics);
                setupFilters();
                filterItems();
                document.getElementById('loading').style.display = 'none';
                document.getElementById('items').style.display = 'grid';
            } catch (error) {
                console.error('Error loading data:', error);
                document.getElementById('loading').innerHTML = 'Error loading data. Please ensure catalog.yml and metrics.yml are available.';
            }
        }
        function updateStats(metrics) {
            const sum = metrics.summary || {};
            const ps = sum.price_stats || {};
            document.getElementById('total-items').textContent = sum.items_total || 0;
            document.getElementById('total-variants').textContent = sum.variants_total || 0;
            document.getElementById('total-shops').textContent = sum.shops_total || 0;
            document.getElementById('total-value').textContent = ps.total_value ? `¥${ps.total_value.toLocaleString()}` : '-';
        }
        function setupFilters() {
            const types = new Set(['all']);
            allItems.forEach(item => types.add(item.type));
            const container = document.getElementById('filters');
            container.innerHTML = '';
            types.forEach(type => {
                const div = document.createElement('div');
                div.className = 'filter' + (type === 'all' ? ' active' : '');
                div.textContent = type.charAt(0).toUpperCase() + type.slice(1);
                div.dataset.type = type;
                div.addEventListener('click', () => setFilter(type));
                container.appendChild(div);
            });
        }
        function setFilter(type) {
            activeFilter = type;
            document.querySelectorAll('.filter').forEach(f => f.classList.remove('active'));
            document.querySelector(`[data-type="${type}"]`).classList.add('active');
            filterItems();
        }
        function filterItems() {
            const term = document.getElementById('search').value.toLowerCase();
            filteredItems = allItems.filter(item => {
                const matchFilter = activeFilter === 'all' || item.type === activeFilter;
                const matchSearch = !term || item.name.toLowerCase().includes(term) || (item.shop_name && item.shop_name.toLowerCase().includes(term)) || (item.targets && item.targets.some(t => t.name.toLowerCase().includes(term) || t.code.toLowerCase().includes(term)));
                return matchFilter && matchSearch;
            });
            renderItems();
        }
        function renderItems() {
            const container = document.getElementById('items');
            if (filteredItems.length === 0) {
                container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 50px; color: #666;">No items found</div>';
                return;
            }
            container.innerHTML = filteredItems.map(item => `
                <div class="item-card">
                    <div class="item-image">${item.image_url ? `<img src="${item.image_url}" alt="${item.name}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 4px;">` : 'No Image'}</div>
                    <div class="item-title"><a href="${item.url}" target="_blank" style="text-decoration: none; color: inherit;">${item.name}</a></div>
                    <div class="item-shop">${item.shop_name || 'Unknown Shop'}</div>
                    <div class="item-price">${item.current_price !== null && item.current_price !== undefined ? (item.current_price === 0 ? 'Free' : `¥${item.current_price.toLocaleString()}`) : 'Price Unknown'}</div>
                    ${item.targets && item.targets.length > 0 ? `<div class="item-targets">${item.targets.map(target => `<span class="target-tag">${target.name}</span>`).join('')}</div>` : ''}
                </div>
            `).join('');
        }
        document.getElementById('search').addEventListener('input', filterItems);
        loadData();
    </script>
</body>
</html>"""
