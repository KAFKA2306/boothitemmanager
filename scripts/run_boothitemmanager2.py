print("DEBUG: Script started")
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import time

"""
run_boothitemmanager2.py - Master Orchestrator for BoothItemManager2 Perfect Copy
===============================================================
Orchestrates: Crawler -> Normalizer -> DB/Graph Builder -> API/Search Index
Usage: python run_boothitemmanager2.py
"""

from boothitemmanager2.db_builder import build_db
from boothitemmanager2.graph_builder import build_graph
from boothitemmanager2.search_builder import build_search_index
from boothitemmanager2.crawler import fetch_html
from boothitemmanager2.api_generator import generate_api
from boothitemmanager2.normalizer import normalize_html
from boothitemmanager2.tag_graph_builder import TagGraphBuilder
from boothitemmanager2.similarity_engine import calculate_similar_items
from boothitemmanager2.staging_buffer import StagingBuffer
from boothitemmanager2.orchestrator import TransactionOrchestrator

# Target IDs for the initial collection
ITEM_IDS = [
    "3984867",  # Aoi
    "4213786",  # INABA/Shiina/KitsuneAme Set
]

def main():
    print("🚀 BoothItemManager2: Initializing Perfect Copy Pipeline...")
if __name__ == '__main__': main()
