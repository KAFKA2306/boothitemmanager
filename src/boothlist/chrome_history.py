import os
import sqlite3
import shutil
import tempfile
import platform
import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import logging

from .input_loader import InputLoader

logger = logging.getLogger(__name__)


class ChromeHistoryExtractor:
    """Extract BOOTH item IDs from Chrome history database."""

    def __init__(self, history_path: Optional[Path] = None):
        self.history_path = history_path or self._find_chrome_history_path()
        # Compile regex patterns from InputLoader
        self.url_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in InputLoader.BOOTH_URL_PATTERNS
        ]

    def _find_chrome_history_path(self) -> Path:
        system = platform.system()
        if system == "Windows":
            base_path = Path.home() / "AppData/Local/Google/Chrome/User Data/Default"
        elif system == "Darwin":  # macOS
            base_path = Path.home() / "Library/Application Support/Google/Chrome/Default"
        else:  # Linux and others
            base_path = Path.home() / ".config/google-chrome/Default"
        history_path = base_path / "History"
        if history_path.exists():
            return history_path
        raise FileNotFoundError(
            f"Chrome history not found at {history_path}. Please ensure Chrome is installed and has been used."
        )

    def extract_booth_id_from_url(self, url: str) -> Optional[int]:
        if not url:
            return None
        for regex in self.url_regex:
            match = regex.search(url)
            if match:
                try:
                    item_id = int(match.group(1))
                    if 1000000 <= item_id <= 99999999:
                        return item_id
                except (ValueError, IndexError):
                    continue
        return None

    def extract_booth_ids(self, days_back: int = 90) -> List[Dict[str, Any]]:
        """Extract BOOTH IDs from Chrome history database."""
        logger.info(f"Extracting BOOTH IDs from last {days_back} days using {self.history_path}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            temp_path = tmp.name
            try:
                shutil.copy2(self.history_path, temp_path)
            except PermissionError:
                raise PermissionError(
                    "Cannot access Chrome history database. Please close Chrome and try again."
                )

        try:
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            cutoff_time = datetime.now() - timedelta(days=days_back)
            webkit_time = int((cutoff_time.timestamp() + 11644473600) * 1000000)
            query = """
            SELECT DISTINCT
                urls.url,
                urls.title,
                urls.visit_count,
                urls.last_visit_time,
                datetime(urls.last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as last_visit
            FROM urls
            WHERE urls.url LIKE '%booth.pm%'
              AND urls.url LIKE '%/items/%'
              AND urls.last_visit_time > ?
            ORDER BY urls.last_visit_time DESC;
            """
            cursor.execute(query, (webkit_time,))
            rows = cursor.fetchall()
            items: List[Dict[str, Any]] = []
            seen_ids = set()
            for url, title, visit_count, last_visit_time, last_visit_readable in rows:
                item_id = self.extract_booth_id_from_url(url)
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    items.append(
                        {
                            "item_id": item_id,
                            "title": title or f"Item {item_id}",
                            "url": f"https://booth.pm/ja/items/{item_id}",
                            "original_url": url,
                            "visit_count": visit_count,
                            "last_visit": last_visit_readable,
                            "last_visit_timestamp": last_visit_time,
                        }
                    )
            conn.close()
            logger.info(f"Found {len(items)} unique BOOTH items in history")
            return items
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def export_to_csv(self, items: List[Dict[str, Any]], output_file: str = "booth_ids.csv"):
        if not items:
            logger.warning("No items to export")
            return
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["item_id", "title", "url", "visit_count", "last_visit"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for item in items:
                writer.writerow(
                    {
                        "item_id": item["item_id"],
                        "title": item["title"],
                        "url": item["url"],
                        "visit_count": item["visit_count"],
                        "last_visit": item["last_visit"],
                    }
                )
        logger.info(f"Exported {len(items)} items to {output_file}")

    def export_id_list(self, items: List[Dict[str, Any]], output_file: str = "booth_item_ids.txt"):
        if not items:
            logger.warning("No items to export")
            return
        with open(output_file, "w", encoding="utf-8") as f:
            for item in items:
                f.write(f"{item['item_id']}\n")
        logger.info(f"Exported {len(items)} item IDs to {output_file}")

    def export_analysis_json(self, items: List[Dict[str, Any]], output_file: str = "booth_analysis.json"):
        if not items:
            logger.warning("No items to analyze")
            return
        item_ids = [item["item_id"] for item in items]
        visit_counts = [item["visit_count"] for item in items]
        daily_activity = Counter()
        for item in items:
            if item["last_visit"]:
                date_str = item["last_visit"].split(" ")[0]
                daily_activity[date_str] += 1
        analysis = {
            "extraction_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_items": len(items),
                "date_range": {
                    "earliest": min(item["last_visit"] for item in items if item["last_visit"]),
                    "latest": max(item["last_visit"] for item in items if item["last_visit"]),
                },
            },
            "statistics": {
                "id_range": {"min": min(item_ids), "max": max(item_ids)},
                "visit_stats": {
                    "total_visits": sum(visit_counts),
                    "avg_visits_per_item": sum(visit_counts) / len(visit_counts),
                    "most_visited": max(visit_counts),
                    "least_visited": min(visit_counts),
                },
            },
            "top_items": sorted(items, key=lambda x: x["visit_count"], reverse=True)[:20],
            "recent_items": sorted(items, key=lambda x: x["last_visit_timestamp"], reverse=True)[:20],
            "daily_activity": dict(daily_activity.most_common(30)),
            "all_item_ids": sorted(item_ids, reverse=True),
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Exported analysis to {output_file}")

    def create_input_csv_for_boothlist(self, items: List[Dict[str, Any]], output_file: str = "input/extracted_booth_ids.csv"):
        if not items:
            logger.warning("No items to export")
            return
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["item_id", "name", "url"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for item in items:
                writer.writerow(
                    {
                        "item_id": item["item_id"],
                        "name": item["title"],
                        "url": item["url"],
                    }
                )
        logger.info(f"Created BoothList-compatible input file: {output_file}")


def main():
    try:
        print("Chrome履歴からBOOTH IDを抽出中...")
        print("=" * 50)
        extractor = ChromeHistoryExtractor()
        items = extractor.extract_booth_ids(days_back=90)
        if not items:
            print("No BOOTH items found in Chrome history.")
            return
        print(f"\n抽出結果: {len(items)}件のBOOTH商品")
        print("-" * 30)
        item_ids = [item["item_id"] for item in items]
        visit_counts = [item["visit_count"] for item in items]
        print(f"ID範囲: {min(item_ids)} - {max(item_ids)}")
        print(f"総訪問回数: {sum(visit_counts)}")
        print(f"平均訪問回数: {sum(visit_counts) / len(visit_counts):.1f}")
        print(f"最新訪問: {items[0]['last_visit'] if items else 'N/A'}")
        print(f"\n最も訪問回数の多い10件:")
        top_items = sorted(items, key=lambda x: x["visit_count"], reverse=True)[:10]
        for i, item in enumerate(top_items, 1):
            print(f"  {i:2d}. {item['item_id']}: {item['title'][:50]} (訪問: {item['visit_count']}回)")
        print("\nファイル出力中...")
        extractor.export_to_csv(items)
        extractor.export_id_list(items)
        extractor.export_analysis_json(items)
        extractor.create_input_csv_for_boothlist(items)
        print("\n出力ファイル:")
        print("  - booth_ids.csv: 詳細な商品情報")
        print("  - booth_item_ids.txt: ID一覧のみ")
        print("  - booth_analysis.json: 詳細分析結果")
        print("  - input/extracted_booth_ids.csv: BoothList入力用")
        print(f"\n抽出完了! {len(items)}件のBOOTH商品IDを取得しました。")
    except FileNotFoundError as e:
        print(f"エラー: {e}")
        print("Chrome がインストールされているか、履歴が存在することを確認してください。")
    except PermissionError as e:
        print(f"アクセスエラー: {e}")
        print("Chrome を完全に終了してから再度実行してください。")
    except Exception as e:
        print(f"予期しないエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
