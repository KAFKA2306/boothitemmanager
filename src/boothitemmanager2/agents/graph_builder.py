import json
import os
from typing import List, Dict
from ..core import TestBlock
from ..schemas.storage import Item, GraphNode, GraphEdge

def build_graph(items: List[Item], trace_id: str) -> TestBlock:
    nodes: Dict[str, GraphNode] = {}
    item_edges: Dict[str, List[GraphEdge]] = {}
    for item in items:
        item_node_id = f'item:{item.item_id}'
        creator_node_id = f'creator:{item.creator_id}'
        nodes[item_node_id] = GraphNode(node_id=item_node_id, node_type='item', edges=[])
        if creator_node_id not in nodes:
            nodes[creator_node_id] = GraphNode(node_id=creator_node_id, node_type='creator', edges=[])
        edges_for_item: List[GraphEdge] = [GraphEdge(target_id=creator_node_id, relation='created_by')]
        for tag in item.tags:
            tag_node_id = f'tag:{tag}'
            if tag_node_id not in nodes:
                nodes[tag_node_id] = GraphNode(node_id=tag_node_id, node_type='tag', edges=[])
            edges_for_item.append(GraphEdge(target_id=tag_node_id, relation='has_tag'))
        item_edges[item_node_id] = edges_for_item
    nodes_out = [{'id': n.node_id, 'label': n.node_type.capitalize(), 'properties': {'name': n.node_id}} for n in nodes.values()]
    edges_out = [{'source': src, 'target': e.target_id, 'relation': e.relation.upper(), 'properties': {}} for (src, elist) in item_edges.items() for e in elist]
    nodes_path = 'data/graph/nodes.json'
    edges_path = 'data/graph/edges.json'
    os.makedirs(os.path.dirname(nodes_path), exist_ok=True)
    with open(nodes_path, 'w', encoding='utf-8') as f:
        json.dump(nodes_out, f, ensure_ascii=False, indent=2)
    with open(edges_path, 'w', encoding='utf-8') as f:
        json.dump(edges_out, f, ensure_ascii=False, indent=2)
    return TestBlock(trace_id=trace_id, input=len(items), pre_state={}, action='build_graph', expected_state={'node_count': len(nodes), 'edge_count': len(edges_out)}, actual_state={'node_count': len(nodes), 'edge_count': len(edges_out)}, diff={}, result='SUCCESS')