import subprocess
import time
import os
import sys

def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open("acquisition.log", "a") as f:
        f.write(full_msg + "\n")

def run_command(cmd):
    log(f"Executing: {cmd}")
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        log(f"  {line.strip()}")
    process.wait()
    return

def main():
    target = 30000
    batch_size = 50
    pages_per_loop = 10
    
    log(f"Starting BoothItemManager2 Master Loop. Target: {target}")
    current_page = 1
    
    while True:
        # Check current progress
        if os.path.exists("input/raw"):
            raw_files = [f for f in os.listdir("input/raw") if f.endswith(".html")]
            current_count = len(raw_files)
        else:
            current_count = 0
            
        print(f"--- Progress: {current_count} / {target} ---")
        
        if current_count >= target:
            print("Target reached!")
            break

        # 1. Discovery (Get more IDs if we don't have enough)
        with open("input/discovered_ids.txt", "r") as f:
            discovered_count = len([l for l in f if l.strip()])
        
        if discovered_count < current_count + 500:
            print(f"--- Discovering IDs (Pages {current_page} to {current_page + pages_per_loop}) ---")
            run_command(f"python3 scripts/discover_ids_range.py {current_page} {current_page + pages_per_loop}")
            current_page += pages_per_loop
            
        # 2. Batch Crawl
        print(f"--- Batch Crawling {batch_size} items ---")
        run_command(f"python3 scripts/batch_crawl.py {batch_size}")
        
        # 3. Update Pipeline
        print("--- Updating Pipeline ---")
        run_command("export PYTHONPATH=$PYTHONPATH:. && python3 -m src.boothitemmanager2.main")
        
        print("Batch complete. Sleeping for 10 seconds...")
        time.sleep(10)

if __name__ == "__main__":
    main()
