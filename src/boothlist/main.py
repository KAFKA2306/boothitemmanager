from pathlib import Path
import yaml

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
            if not metadata or (metadata.error and "not found" in metadata.error.lower()):
                continue
            normalized_items.append(self.normalizer.normalize_item(raw_item, metadata))

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

