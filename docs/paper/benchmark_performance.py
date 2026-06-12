import json
import time
import random
import sys
import threading
from pathlib import Path
from collections import Counter

# Path setup
DATA_DIR = Path("data")
CATALOG_PATH = DATA_DIR / "structured" / "catalog.json"
NODES_PATH = DATA_DIR / "graph" / "nodes.json"
EDGES_PATH = DATA_DIR / "graph" / "edges.json"
API_PATH = Path("api") / "catalog_summary_part1.json"

def run_verification_benchmark():
    print("⏳ Loading data layers for benchmarking...")
    
    t0 = time.perf_counter()
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)
        with open(NODES_PATH, "r", encoding="utf-8") as f:
            nodes = json.load(f)
        with open(EDGES_PATH, "r", encoding="utf-8") as f:
            edges = json.load(f)
        with open(API_PATH, "r", encoding="utf-8") as f:
            api_index = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    t_load = time.perf_counter() - t0
    print(f"Data Loaded: Catalog={len(catalog)}, Nodes={len(nodes)}, Edges={len(edges)}, API={len(api_index)}")
    print(f"Load Latency: {t_load*1000:.2f} ms")

    # 1. Benchmark: Structured Layer Validation
    latencies_struct = []
    for _ in range(5):
        t_start = time.perf_counter()
        for item in catalog[:1000]:  # sample check
            _ = item.get("item_id") and item.get("category")
        latencies_struct.append(time.perf_counter() - t_start)
    avg_struct_ms = (sum(latencies_struct) / len(latencies_struct)) * 1000

    # 2. Benchmark: Key-Preserving Edge Alignment Check (O(V+E) verification)
    latencies_align = []
    node_ids = {n["id"] for n in nodes}
    for _ in range(5):
        t_start = time.perf_counter()
        orphans = [e for e in edges if e["target"] not in node_ids]
        _ = len(orphans) == 0
        latencies_align.append(time.perf_counter() - t_start)
    avg_align_ms = (sum(latencies_align) / len(latencies_align)) * 1000
    
    print(f"Average Structured Validation Latency (1k sample): {avg_struct_ms:.3f} ms")
    print(f"Average Key-Preserving Alignment Verification Latency (Full Graph): {avg_align_ms:.3f} ms")

    # 3. Simulate REAL OCC Concurrency & Abort Rate
    # We spawn M actual concurrent worker threads attempting to update hot ontology keys.
    # We measure actual write conflicts and aborted transactions.
    print("\n⏳ Running Real Multithreaded OCC Concurrency Simulation...")
    concurrency_levels = [1, 5, 10, 20, 50]
    registry_size = 100  # number of hot ontology keys
    results = {}
    
    for M in concurrency_levels:
        # State representing hot ontology registry keys: {key_index: version}
        active_versions = {i: 0 for i in range(registry_size)}
        version_lock = threading.Lock()
        
        aborted_txs = [0]
        total_txs_per_thread = 200
        
        def worker():
            for _ in range(total_txs_per_thread):
                target_key = random.randint(0, registry_size - 1)
                
                # 1. Read Phase
                with version_lock:
                    read_version = active_versions[target_key]
                
                # Simulate tiny processing/network delay to create overlapping reads
                time.sleep(random.uniform(0.0001, 0.001))
                
                # 2. Write/Commit Phase (atomic check and increment)
                with version_lock:
                    current_version = active_versions[target_key]
                    if read_version == current_version:
                        # Transaction success, commit write by incrementing version
                        active_versions[target_key] += 1
                    else:
                        # Transaction conflict, abort
                        aborted_txs[0] += 1

        # Spawn threads
        threads = [threading.Thread(target=worker) for _ in range(M)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        total_attempted_txs = M * total_txs_per_thread
        abort_rate = (aborted_txs[0] / total_attempted_txs) * 100
        results[M] = abort_rate
        print(f"Concurrency M={M:2d} threads | Total Txs: {total_attempted_txs} | Aborts: {aborted_txs[0]} | Abort Rate: {abort_rate:5.1f}%")

    print("\n% ==================== ACTUAL LATEX STATS ====================")
    print(f"\\def\\LoadLatencyMs{{{t_load*1000:.1f}}}")
    print(f"\\def\\GraphVerifyLatencyMs{{{avg_align_ms:.1f}}}")
    for M, rate in results.items():
        print(f"\\def\\OCCAbortRateM{M}{{{rate:.1f}}}")

if __name__ == "__main__":
    run_verification_benchmark()
