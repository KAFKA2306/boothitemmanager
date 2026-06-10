import requests
import re
import sys
import os

def discover(start_page, end_page):
    input_file = "input/discovered_ids.txt"
    os.makedirs("input", exist_ok=True)
    
    discovered = set()
    if os.path.exists(input_file):
        with open(input_file, "r") as f:
            discovered = set(line.strip() for line in f if line.strip())

    headers = {"User-Agent": "Mozilla/5.0"}
    new_count = 0

    for page in range(start_page, end_page + 1):
        print(f"Searching page {page}...")
        url = f"https://booth.pm/ja/search/VRChat?page={page}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            
            ids = re.findall(r"items/([0-9]+)", res.text)
            for i in sorted(set(ids)):
                if i not in discovered:
                    with open(input_file, "a") as f:
                        f.write(f"{i}\n")
                    discovered.add(i)
                    new_count += 1
        except Exception as e:
            print(f"Error on page {page}: {e}")
    
    print(f"Range {start_page}-{end_page} done. New IDs: {new_count}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 discover_ids_range.py <start> <end>")
    else:
        discover(int(sys.argv[1]), int(sys.argv[2]))
