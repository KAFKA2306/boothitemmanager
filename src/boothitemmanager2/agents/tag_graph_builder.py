import json
import yaml
import itertools
from pathlib import Path
from collections import Counter, defaultdict
from dataclasses import asdict
from typing import List, Dict, Set, Tuple, Any

try:
    from .schemas.storage import TagNode, TagEdge, TagGraph
except ImportError:
    # Handle direct execution or different path
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from boothitemmanager2.schemas.storage import TagNode, TagEdge, TagGraph

class TagGraphBuilder:
    def __init__(self, catalog_path: Path, aliases_path: Path, output_path: Path):
        self.catalog_path = catalog_path
        self.aliases_path = aliases_path
        self.output_path = output_path
        self.min_score = 0.01

    def load_ontology(self) -> Dict[str, str]:
        """Maps tags to dimensions based on aliases.yml"""
        if not self.aliases_path.exists():
            return {}
        
        with open(self.aliases_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        tag_to_dim = {}
        
        # Mapping for avatars
        if "avatars" in data:
            for avatar_id in data["avatars"]:
                tag_to_dim[avatar_id] = "avatar"
        
        # Mapping based on mood_tags structure (heuristic dimension assignment)
        appearance = {"silver_hair", "black_hair", "long_hair", "twin_tails", "cat_ears", "beast_ears"}
        style = {"japanese", "maid", "sport", "gothic", "cyber", "fantasy"}
        season = {"summer", "winter", "waso"}
        
        if "mood_tags" in data:
            for tag_key, info in data["mood_tags"].items():
                dim = "general"
                if tag_key in appearance: dim = "appearance"
                elif tag_key in style: dim = "style"
                elif tag_key in season: dim = "season"
                
                tag_to_dim[tag_key] = dim
                # Add aliases as well
                for alias in info.get("aliases", []):
                    tag_to_dim[alias] = dim
                if "name_ja" in info: tag_to_dim[info["name_ja"]] = dim
                if "name_en" in info: tag_to_dim[info["name_en"]] = dim

        return tag_to_dim

    def build(self):
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Catalog not found at {self.catalog_path}")

        print(f"Loading catalog from {self.catalog_path}...")
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            try:
                items = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse catalog JSON: {e}")

        if not isinstance(items, list):
            raise TypeError(f"Expected list of items in catalog, got {type(items)}")
        
        if not items:
            print("Warning: Catalog is empty. No graph will be generated.")
            return

        tag_to_dim = self.load_ontology()
        
        tag_counts = Counter()
        co_occurrence = Counter()
        tag_names = {}

        print(f"Processing {len(items)} items...")
        for item in items:
            # Combine raw tags, generated tags, and avatar targets
            tags = set(item.get("tags_raw", []) + item.get("tags_generated", []))
            for target in item.get("targets", []):
                if isinstance(target, dict) and "code" in target:
                    tags.add(target["code"])
                elif isinstance(target, str):
                    tags.add(target)

            # Clean tags
            tags = {t.strip() for t in tags if t.strip()}
            
            for tag in tags:
                tag_counts[tag] += 1
                if tag not in tag_names:
                    tag_names[tag] = tag
            
            if len(tags) > 1:
                # Count pairs (sorted to ensure consistency)
                for t1, t2 in itertools.combinations(sorted(list(tags)), 2):
                    co_occurrence[(t1, t2)] += 1

        print("Calculating Jaccard scores...")
        nodes_dict = {}
        edges = []

        # Jaccard = |A n B| / |A u B|
        # |A u B| = |A| + |B| - |A n B|
        for (t1, t2), intersect_count in co_occurrence.items():
            union_count = tag_counts[t1] + tag_counts[t2] - intersect_count
            score = intersect_count / union_count if union_count > 0 else 0
            
            if score >= self.min_score:
                edges.append(TagEdge(source_id=t1, target_id=t2, strength=round(score, 4)))
                # Mark tags for inclusion in nodes
                nodes_dict[t1] = nodes_dict.get(t1, tag_counts[t1])
                nodes_dict[t2] = nodes_dict.get(t2, tag_counts[t2])

        print(f"Generating {len(nodes_dict)} nodes and {len(edges)} edges...")
        nodes = []
        for tag_id, count in nodes_dict.items():
            nodes.append(TagNode(
                tag_id=tag_id,
                name=tag_names.get(tag_id, tag_id),
                dimension=tag_to_dim.get(tag_id, "general"),
                weight=count
            ))

        graph = TagGraph(nodes=nodes, edges=edges)
        
        print(f"Saving to {self.output_path}...")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(graph), f, ensure_ascii=False, indent=2)

        print("Done! 💕")

def build_tag_graph(items: List[Dict[str, Any]], trace_id: str):
    """Architectural bridge to run the builder from the master pipeline."""
    # The builder currently reads from file for 40k items efficiency, 
    # but we'll ensure api/catalog.json is updated before calling this 
    # in the master script.
    builder = TagGraphBuilder(
        catalog_path=Path("api/catalog.json"),
        aliases_path=Path("aliases.yml"),
        output_path=Path("api/tag_graph.json")
    )
    builder.build()

if __name__ == "__main__":
    builder = TagGraphBuilder(
        catalog_path=Path("api/catalog.json"),
        aliases_path=Path("aliases.yml"),
        output_path=Path("api/tag_graph.json")
    )
    builder.build()
