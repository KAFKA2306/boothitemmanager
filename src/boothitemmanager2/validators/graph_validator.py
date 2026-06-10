import json
import os
from ..core import TestBlock, Message

def validate_graph(block: TestBlock) -> Message:
    nodes_path = block.actual_state.get('nodes_path', 'data/graph/nodes.json')
    edges_path = block.actual_state.get('edges_path', 'data/graph/edges.json')
    nodes_exist = os.path.exists(nodes_path)
    edges_exist = os.path.exists(edges_path)
    node_count = 0
    edge_count = 0
    if nodes_exist:
        with open(nodes_path, 'r', encoding='utf-8') as f:
            node_count = len(json.load(f))
    if edges_exist:
        with open(edges_path, 'r', encoding='utf-8') as f:
            edge_count = len(json.load(f))
    expected_nodes = block.expected_state.get('node_count', 0)
    expected_edges = block.expected_state.get('edge_count', 0)
    is_valid = nodes_exist and edges_exist and (node_count == expected_nodes) and (edge_count == expected_edges)
    status = 'SUCCESS' if is_valid else 'WARNING'
    payload = {'status': status, 'nodes_verified': nodes_exist, 'edges_verified': edges_exist, 'counts': {'nodes': {'expected': expected_nodes, 'actual': node_count}, 'edges': {'expected': expected_edges, 'actual': edge_count}}}
    return Message(from_agent='graph_validator', to_agent='main_agent', trace_id=block.trace_id, payload=payload)