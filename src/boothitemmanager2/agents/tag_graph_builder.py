import json
import itertools
from pathlib import Path
from collections import Counter
from dataclasses import asdict
try:
    from ..schemas.storage import TagNode, TagEdge, TagGraph
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent.parent.parent))
    from boothitemmanager2.schemas.storage import TagNode, TagEdge, TagGraph

class TagGraphBuilder:

    def __init__(self, catalog_path: Path, aliases_path: Path, output_path: Path):
        self.catalog_path = catalog_path
        self.aliases_path = aliases_path
        self.output_path = output_path
        self.min_score = 0.01

    def build(self):
        if not self.catalog_path.exists():
            raise FileNotFoundError(f'Catalog not found at {self.catalog_path}')
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            items = json.load(f)
        tag_counts = Counter()
        co_occurrence = Counter()
        tag_to_dim = {}
        print(f'Building graph for {len(items)} items...')
        for item in items:
            item_tags = set(item.get('tags_raw', []))
            tag_set = item.get('tag_set', {})
            for (dim, values) in tag_set.items():
                if isinstance(values, list):
                    for v in values:
                        item_tags.add(v)
                        tag_to_dim[v] = dim
            for target in item.get('targets', []):
                code = target.get('code') if isinstance(target, dict) else None
                if code:
                    item_tags.add(code)
                    tag_to_dim[code] = 'avatar_link'
            tags = sorted([t.strip() for t in item_tags if t.strip()])
            for tag in tags:
                tag_counts[tag] += 1
            if len(tags) > 1:
                for (t1, t2) in itertools.combinations(tags, 2):
                    co_occurrence[t1, t2] += 1
        nodes_dict = {}
        edges = []
        for ((t1, t2), intersect_count) in co_occurrence.items():
            union_count = tag_counts[t1] + tag_counts[t2] - intersect_count
            score = intersect_count / union_count if union_count > 0 else 0
            if score >= self.min_score:
                edges.append(TagEdge(source_id=t1, target_id=t2, strength=round(score, 4)))
                nodes_dict[t1] = tag_counts[t1]
                nodes_dict[t2] = tag_counts[t2]
        nodes = [TagNode(tag_id=tid, name=tid, dimension=tag_to_dim.get(tid, 'general'), weight=count) for (tid, count) in nodes_dict.items()]
        graph = TagGraph(nodes=nodes, edges=edges)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(graph), f, ensure_ascii=False, indent=2)
        print(f'Graph built: {len(nodes)} nodes, {len(edges)} edges. 💕')
if __name__ == '__main__':
    builder = TagGraphBuilder(catalog_path=Path('api/catalog.json'), aliases_path=Path('aliases.yml'), output_path=Path('api/tag_graph.json'))
    builder.build()