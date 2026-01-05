import yaml
from pathlib import Path
from boothlist.scrape import BoothScraper

def main():
    ids = [
        73097838, 70787649, 70667040, 65755217, 
        5468117, 51335035, 7018378, 42436576, 43962216
    ]
    
    scraper = BoothScraper(cache_file="booth_item_cache.json", rate_limit=1.0)
    results = scraper.scrape_items(ids)
    
    lines = ["# Inner Contents (Related Items)\n"]
    for item_id, meta in results.items():
        lines.append(f"## Item {item_id}")
        if meta.name:
            lines.append(f"Name: {meta.name}")
        
        if meta.related_item_ids:
            lines.append("Related Item IDs:")
            for related in meta.related_item_ids:
                lines.append(f"- {related}")
        else:
            lines.append("No related items found.")
        lines.append("")
        
    Path("docs/inner_contents.md").write_text("\n".join(lines), encoding="utf-8")
    print("Generated docs/inner_contents.md")

if __name__ == "__main__":
    main()
