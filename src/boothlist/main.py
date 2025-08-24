"""Main ETL pipeline orchestration script for BoothList."""

import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import argparse

from .input_loader import InputLoader, RawItem
from .scrape import BoothScraper, ItemMetadata
from .normalize import DataNormalizer, Item
from .export import CatalogExporter, HTMLDashboardExporter

logger = logging.getLogger(__name__)


class BoothListETL:
    """Main ETL pipeline orchestrator for BoothList."""
    
    def __init__(self, input_dir: str = 'input', cache_file: str = 'booth_item_cache.json', 
                 output_dir: str = 'dist', rate_limit: float = 1.0):
        """Initialize the ETL pipeline.
        
        Args:
            input_dir: Directory containing input files
            cache_file: Path to cache file for scraped metadata
            output_dir: Directory for output files
            rate_limit: Seconds between scraping requests
        """
        self.input_dir = Path(input_dir)
        self.cache_file = cache_file
        self.output_dir = Path(output_dir)
        self.rate_limit = rate_limit
        
        # Initialize components
        self.loader = InputLoader()
        self.scraper = BoothScraper(cache_file=cache_file, rate_limit=rate_limit)
        self.normalizer = DataNormalizer()
        self.catalog_exporter = CatalogExporter()
        self.html_exporter = HTMLDashboardExporter()
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def run_full_pipeline(self, force_refresh: bool = False) -> bool:
        """Run the complete ETL pipeline.
        
        Args:
            force_refresh: Force refresh of cached metadata
            
        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting BoothList ETL pipeline")
        start_time = time.time()
        
        try:
            # Step 1: Load input data
            logger.info("Step 1: Loading input data")
            raw_items = self.load_input_data()
            if not raw_items:
                logger.error("No items loaded from input data")
                return False
            logger.info(f"Loaded {len(raw_items)} items from input")
            
            # Step 2: Scrape metadata
            logger.info("Step 2: Scraping BOOTH metadata")
            metadata_dict = self.scrape_metadata(raw_items, force_refresh=force_refresh)
            logger.info(f"Scraped metadata for {len(metadata_dict)} items")
            
            # Step 3: Normalize data
            logger.info("Step 3: Normalizing data")
            normalized_items = self.normalize_data(raw_items, metadata_dict)
            logger.info(f"Normalized {len(normalized_items)} items")
            
            # Step 4: Export outputs
            logger.info("Step 4: Exporting outputs")
            success = self.export_outputs(normalized_items)
            if not success:
                logger.error("Failed to export outputs")
                return False
            
            # Step 5: Generate reports
            self.generate_reports(raw_items, metadata_dict, normalized_items)
            
            elapsed_time = time.time() - start_time
            logger.info(f"ETL pipeline completed successfully in {elapsed_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"ETL pipeline failed: {e}", exc_info=True)
            return False
    
    def load_input_data(self) -> List[RawItem]:
        """Load and validate input data."""
        raw_items = self.loader.load_from_directory(self.input_dir)
        validated_items = self.loader.validate_items(raw_items)
        return validated_items
    
    def scrape_metadata(self, raw_items: List[RawItem], force_refresh: bool = False) -> Dict[int, ItemMetadata]:
        """Scrape metadata for all items."""
        item_ids = [item.item_id for item in raw_items]
        metadata_dict = self.scraper.scrape_items(item_ids, force_refresh=force_refresh)
        return metadata_dict
    
    def normalize_data(self, raw_items: List[RawItem], metadata_dict: Dict[int, ItemMetadata]) -> List[Item]:
        """Normalize raw data and metadata to structured format."""
        normalized_items = []
        
        for raw_item in raw_items:
            metadata = metadata_dict.get(raw_item.item_id)
            if not metadata:
                logger.warning(f"No metadata found for item {raw_item.item_id}")
                # Create empty metadata
                metadata = ItemMetadata(item_id=raw_item.item_id, error="No metadata")
            
            # Skip items with critical errors
            if metadata.error and "not found" in metadata.error.lower():
                logger.warning(f"Skipping item {raw_item.item_id}: {metadata.error}")
                continue
            
            normalized_item = self.normalizer.normalize_item(raw_item, metadata)
            normalized_items.append(normalized_item)
        
        return normalized_items
    
    def export_outputs(self, items: List[Item]) -> bool:
        """Export all output files."""
        try:
            # Export catalog.yml
            catalog_path = self.output_dir / 'catalog.yml'
            success = self.catalog_exporter.export_catalog(items, str(catalog_path))
            if not success:
                return False
            
            # Export metrics.yml
            metrics_path = self.output_dir / 'metrics.yml'
            success = self.catalog_exporter.export_metrics(items, str(metrics_path))
            if not success:
                return False
            
            # Export index.html
            html_path = self.output_dir / 'index.html'
            success = self.html_exporter.export_dashboard(str(html_path))
            if not success:
                return False
            
            logger.info(f"Exported outputs to {self.output_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting outputs: {e}")
            return False
    
    def generate_reports(self, raw_items: List[RawItem], metadata_dict: Dict[int, ItemMetadata], 
                        normalized_items: List[Item]):
        """Generate processing reports."""
        total_raw = len(raw_items)
        total_metadata = len(metadata_dict)
        total_normalized = len(normalized_items)
        
        # Count metadata errors
        metadata_errors = sum(1 for meta in metadata_dict.values() if meta.error)
        metadata_success = total_metadata - metadata_errors
        
        # Count by type
        type_counts = {}
        for item in normalized_items:
            type_counts[item.type] = type_counts.get(item.type, 0) + 1
        
        # Count avatar targets
        avatar_counts = {}
        for item in normalized_items:
            for target in item.targets:
                avatar_counts[target.code] = avatar_counts.get(target.code, 0) + 1
        
        # Cache statistics
        cache_stats = self.scraper.get_cache_stats()
        
        # Print report
        print("\n" + "="*60)
        print("BOOTHLIST ETL PIPELINE REPORT")
        print("="*60)
        print(f"Input Processing:")
        print(f"  Raw items loaded:      {total_raw}")
        print(f"  Items normalized:      {total_normalized}")
        print()
        print(f"Metadata Scraping:")
        print(f"  Items scraped:         {total_metadata}")
        print(f"  Successful:            {metadata_success}")
        print(f"  Errors:                {metadata_errors}")
        print()
        print(f"Cache Statistics:")
        print(f"  Total entries:         {cache_stats['total_entries']}")
        print(f"  Success entries:       {cache_stats['success_entries']}")
        print(f"  Error entries:         {cache_stats['error_entries']}")
        print()
        print(f"Item Types:")
        for item_type, count in sorted(type_counts.items()):
            print(f"  {item_type:15}: {count}")
        print()
        print(f"Avatar Targets:")
        for avatar, count in sorted(avatar_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {avatar:15}: {count}")
        print()
        print(f"Output Files:")
        print(f"  {self.output_dir / 'catalog.yml'}")
        print(f"  {self.output_dir / 'metrics.yml'}")
        print(f"  {self.output_dir / 'index.html'}")
        print("="*60)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point with command line interface."""
    parser = argparse.ArgumentParser(
        description='BoothList ETL Pipeline - Process BOOTH purchase data into searchable dashboard'
    )
    parser.add_argument(
        '--input-dir', '-i',
        default='input',
        help='Input directory containing YAML/CSV/Markdown files (default: input)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='dist',
        help='Output directory for generated files (default: dist)'
    )
    parser.add_argument(
        '--cache-file', '-c',
        default='booth_item_cache.json',
        help='Cache file for scraped metadata (default: booth_item_cache.json)'
    )
    parser.add_argument(
        '--rate-limit', '-r',
        type=float,
        default=1.0,
        help='Rate limit in seconds between scraping requests (default: 1.0)'
    )
    parser.add_argument(
        '--force-refresh', '-f',
        action='store_true',
        help='Force refresh of cached metadata'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    # Create and run ETL pipeline
    etl = BoothListETL(
        input_dir=args.input_dir,
        cache_file=args.cache_file,
        output_dir=args.output_dir,
        rate_limit=args.rate_limit
    )
    
    success = etl.run_full_pipeline(force_refresh=args.force_refresh)
    
    if success:
        print("\nETL pipeline completed successfully!")
        print(f"Dashboard available at: {Path(args.output_dir) / 'index.html'}")
        sys.exit(0)
    else:
        print("\nETL pipeline failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()