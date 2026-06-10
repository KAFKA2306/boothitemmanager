import requests
import sys
import os
import time

def crawl(limit):
    input_file = "input/discovered_ids.txt"
    raw_dir = "input/raw"
    os.makedirs(raw_dir, exist_ok=True)
    
    with open(input_file, "r") as f:
        ids = [line.strip() for line in f if line.strip()]
    
    headers = {"User-Agent": "Mozilla/5.0"}
    count = 0
    
    for i in ids:
        if count >= limit:
            break
            
        path = f"{raw_dir}/{i}.html"
        if os.path.exists(path):
            continue
            
        print(f"Fetching {i}...")
        res = requests.get(f"https://booth.pm/ja/items/{i}", headers=headers)
        res.raise_for_status()
        
        with open(path, "w") as f:
            f.write(res.text)
        
        count += 1
        time.sleep(2.5)

    print(f"Done. Crawled: {count}")

if __name__ == "__main__":
    crawl(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
