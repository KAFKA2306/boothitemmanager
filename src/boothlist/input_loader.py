import csv
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class RawItem:
    item_id: int
    name: str | None = None
    author: str | None = None
    category: str | None = None
    variation: str | None = None
    files: list[str] = None
    url: str | None = None
    notes: str | None = None
    wish_price: int | None = None

    def __post_init__(self):
        if self.files is None:
            self.files = []


class InputLoader:
    BOOTH_URL_PATTERNS = [
        r"https?://booth\.pm/(?:ja/|en/)?items/(\d+)",
        r"https?://[\w-]+\.booth\.pm/items/(\d+)",
        r"booth\.pm/(?:ja/|en/)?items/(\d+)",
        r"items/(\d+)(?:[/?#]|$)",
        r"booth\.pm/items/(\d+)",
        r"booth\.pm/(\d+)",
        r"/items/(\d+)",
        r"item[_-]?id[=:](\d+)",
        r"(?:item|product)[_-]?(\d+)",
        r"(\d{7,8})(?:[^\d]|$)",
    ]

    def __init__(self):
        self.url_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.BOOTH_URL_PATTERNS
        ]

    def extract_item_id(self, text: str) -> int | None:
        if not text:
            return None
        for regex in self.url_regex:
            if match := regex.search(text):
                return int(match.group(1))
        return None

    def load_yaml(self, file_path: str | Path) -> list[RawItem]:
        file_path = Path(file_path)
        if not file_path.exists():
            return []

        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        items = []
        for item_data in data.get("booth_purchases", []):
            if not (item_id := item_data.get("id")):
                continue

            raw_item = RawItem(
                item_id=item_id,
                name=item_data.get("name"),
                author=item_data.get("author"),
                category=item_data.get("category"),
                variation=item_data.get("variation"),
                files=item_data.get("files", []),
                notes=item_data.get("notes"),
                wish_price=item_data.get("wish_price"),
            )
            raw_item.url = f"https://booth.pm/ja/items/{item_id}"
            items.append(raw_item)
        return items

    def load_markdown(self, file_path: str | Path) -> list[RawItem]:
        file_path = Path(file_path)
        if not file_path.exists():
            return []

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        items = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            if item_id := self.extract_item_id(line):
                md_link_match = re.search(r"\[([^\]]+)\]\([^)]+\)", line)
                name = md_link_match.group(1) if md_link_match else None
                items.append(
                    RawItem(
                        item_id=item_id, name=name, url=f"https://booth.pm/ja/items/{item_id}"
                    )
                )

        seen_ids = set()
        unique_items = []
        for item in items:
            if item.item_id not in seen_ids:
                seen_ids.add(item.item_id)
                unique_items.append(item)
        return unique_items

    def load_csv(self, file_path: str | Path) -> list[RawItem]:
        file_path = Path(file_path)
        if not file_path.exists():
            return []

        items = []
        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = None
                for col in ["id", "item_id", "url", "link"]:
                    if col in row and row[col]:
                        if extracted_id := self.extract_item_id(str(row[col])):
                            item_id = extracted_id
                            break
                if not item_id:
                    continue

                items.append(
                    RawItem(
                        item_id=item_id,
                        name=row.get("name") or row.get("title"),
                        author=row.get("author") or row.get("creator") or row.get("shop"),
                        category=row.get("category") or row.get("type"),
                        variation=row.get("variation") or row.get("variant"),
                        notes=row.get("notes") or row.get("memo"),
                        wish_price=self._parse_price(row.get("price") or row.get("wish_price")),
                        url=f"https://booth.pm/ja/items/{item_id}",
                    )
                )
        return items

    def _parse_price(self, price_str: str | None) -> int | None:
        if not price_str:
            return None
        price_clean = re.sub(r"[¥,\s]", "", str(price_str))
        return int(price_clean) if price_clean.isdigit() else None

    def load_from_directory(self, input_dir: str | Path) -> list[RawItem]:
        input_dir = Path(input_dir)
        if not input_dir.exists():
            return []

        all_items = []
        for yaml_file in input_dir.glob("*.yaml"):
            all_items.extend(self.load_yaml(yaml_file))
        for yml_file in input_dir.glob("*.yml"):
            all_items.extend(self.load_yaml(yml_file))
        for md_file in input_dir.glob("*.md"):
            all_items.extend(self.load_markdown(md_file))
        for csv_file in input_dir.glob("*.csv"):
            all_items.extend(self.load_csv(csv_file))

        seen_ids = set()
        unique_items = []
        for item in all_items:
            if item.item_id not in seen_ids:
                seen_ids.add(item.item_id)
                unique_items.append(item)
        return unique_items

    def validate_items(self, items: list[RawItem]) -> list[RawItem]:
        valid_items = []
        for item in items:
            if not item.item_id:
                continue
            if not isinstance(item.item_id, int) or item.item_id <= 0:
                continue
            if not (1000000 <= item.item_id <= 99999999):
                continue
            if not item.url:
                item.url = f"https://booth.pm/ja/items/{item.item_id}"
            valid_items.append(item)
        return valid_items
