from pathlib import Path
import yaml
from collections import defaultdict
from .export import CatalogExporter, HTMLDashboardExporter
from .input_loader import InputLoader
from .normalize import DataNormalizer
from .scrape import BoothScraper
class BoothListETL:
    def __init__(self, config):
        self.config = config
        self.output_dir = Path(config.get("output_dir", "dist"))
        self.loader = InputLoader()
        self.scraper = BoothScraper(
            cache_file=config.get("cache_file", "booth_item_cache.json"),
            rate_limit=config.get("rate_limit", 1.0)
        )
        self.normalizer = DataNormalizer()
        self.catalog_exporter = CatalogExporter()
        self.html_exporter = HTMLDashboardExporter()
        self.output_dir.mkdir(parents=True, exist_ok=True)
    def run(self):
        raw_items = self.loader.load_from_directory(Path(self.config.get("input_dir", "input")))
        validated_items = self.loader.validate_items(raw_items)
        item_ids = [item.item_id for item in validated_items]
        metadata_dict = self.scraper.scrape_items(item_ids, force_refresh=self.config.get("force_refresh", False))
        normalized_items = []
        for raw_item in validated_items:
            metadata = metadata_dict.get(raw_item.item_id)
            if not metadata:
                continue
            normalized_items.append(self.normalizer.normalize_item(raw_item, metadata))
        mochifitter_ids = set()
        mochifitter_csv = Path(self.config.get("input_dir", "input")) / "mochifitter_avatars.csv"
        if mochifitter_csv.exists():
            import csv
            with open(mochifitter_csv, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if iid := row.get("item_id"):
                        if iid.isdigit():
                            mochifitter_ids.add(int(iid))
        owned_avatar_ids = {item.item_id for item in normalized_items if item.type == "avatar"}
        id_to_codes = defaultdict(set)
        if mochifitter_csv.exists():
            with open(mochifitter_csv, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if iid := row.get("item_id"):
                        name = row.get("name", "")
                        if code := self.normalizer.avatar_dict.normalize_avatar(name):
                             id_to_codes[int(iid)].add(code)
        for item in normalized_items:
             if item.type == "avatar":
                 if code := self.normalizer.avatar_dict.normalize_avatar(item.name):
                     id_to_codes[item.item_id].add(code)
        owned_codes = set()
        for iid in owned_avatar_ids:
            owned_codes.update(id_to_codes.get(iid, []))
        mochifitter_codes = set()
        for iid in mochifitter_ids:
            mochifitter_codes.update(id_to_codes.get(iid, []))
        for item in normalized_items:
             if not item.targets:
                 continue
             is_owned = False
             is_mochi = False
             for target in item.targets:
                 if target.code in owned_codes:
                     is_owned = True
                 if target.code in mochifitter_codes:
                     is_mochi = True
             if is_owned:
                 item.tags.append("owned_support")
             elif is_mochi:
                 item.tags.append("mochifitter_support")
             else:
                 item.tags.append("orphaned_support")
        self.catalog_exporter.export_catalog(normalized_items, str(self.output_dir / "catalog.yml"))
        self.catalog_exporter.export_metrics(normalized_items, str(self.output_dir / "metrics.yml"))
        self.html_exporter.export_dashboard(str(self.output_dir / "index.html"))
def load_config():
    if Path("config.yaml").exists():
        with open("config.yaml") as f:
            return yaml.safe_load(f)
    return {}
def main():
    config = load_config()
    etl = BoothListETL(config)
    etl.run()
if __name__ == "__main__":
    main()
