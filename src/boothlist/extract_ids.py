import sys
from datetime import datetime
from pathlib import Path
from boothlist.input_loader import InputLoader
def main():
    print("Paste text containing Booth URLs or IDs (Ctrl+D to finish):", file=sys.stderr)
    try:
        text = sys.stdin.read()
    except KeyboardInterrupt:
        return
    unique_ids = set()
    today_doc_path = Path(f"input/{datetime.now().strftime('%Y%m%d')}.txt")
    if today_doc_path.exists():
        with open(today_doc_path, encoding="utf-8") as f:
            for line in f:
                if line.strip().isdigit():
                    unique_ids.add(int(line.strip()))
    loader = InputLoader()
    for line in text.splitlines():
        for regex in loader.url_regex:
            for match in regex.finditer(line):
                unique_ids.add(int(match.group(1)))
    if not unique_ids:
        print("No IDs found (new or existing).", file=sys.stderr)
        return
    today_doc_path.parent.mkdir(exist_ok=True)
    with open(today_doc_path, "w", encoding="utf-8") as f:
        for i in sorted(unique_ids):
            f.write(f"{i}\n")
    print(f"Total {len(unique_ids)} unique IDs saved to {today_doc_path}", file=sys.stderr)
if __name__ == "__main__":
    main()
