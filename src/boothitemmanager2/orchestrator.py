import json
import os
import shutil
from typing import Any, Dict

class TransactionOrchestrator:
    """
    2-Phase Commit (2PC) Orchestrator for atomic updates to multiple storage layers.
    Zero-Fat implementation following CDD.
    """
    STAGING_DIR = ".transaction_staging"

    def __init__(self, trace_id: str):
        self.trace_id = trace_id
        self.participants: Dict[str, str] = {} # target_path -> staging_path

    def prepare(self, target_path: str, data: Any):
        if not os.path.exists(self.STAGING_DIR):
            os.makedirs(self.STAGING_DIR, exist_ok=True)
        
        staging_filename = f"{self.trace_id}_{os.path.basename(target_path)}.tmp"
        staging_path = os.path.join(self.STAGING_DIR, staging_filename)
        
        with open(staging_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.participants[target_path] = staging_path

    def commit(self):
        # Phase 2: Commit (Atomic Renames)
        # Crash-Driven: If rename fails, it crashes, providing stack trace.
        for target_path, staging_path in self.participants.items():
            target_dir = os.path.dirname(target_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            # Atomic rename (POSIX)
            os.replace(staging_path, target_path)
        
        # Cleanup
        if os.path.exists(self.STAGING_DIR) and not os.listdir(self.STAGING_DIR):
            os.rmdir(self.STAGING_DIR)

    def rollback(self):
        # Cleanup staging files
        for staging_path in self.participants.values():
            if os.path.exists(staging_path):
                os.remove(staging_path)
