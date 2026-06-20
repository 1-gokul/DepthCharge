"""
network.py
Builds the microservice dependency graph using NetworkX.
Calculates centrality scores to identify the most critical services.
"""

import networkx as nx
from typing import List, Dict
from models import Service, Dependency, RiskScore
from database import get_all_services, get_all_dependencies, save_risk_score


def build_graph(
    services: List[Service],
    dependencies: List[Dependency]
) -> nx.DiGraph:
    """
    Builds a directed graph from services and dependencies.

    Nodes  = services
    Edges  = dependencies (source depends on target)
    Weight = strength of dependency

    Returns a NetworkX DiGraph.
    """
    graph = nx.DiGraph()

    # add all services as nodes
    for service in services:
        graph.add_node(
            service.id,
            name=service.name,
            team=service.team,
            criticality=service.criticality,
            failure_rate=service.failure_rate,
            is_active=service.is_active
        )

    # add all dependencies as edges
    for dep in dependencies:
        graph.add_edge(
            dep.source_id,
            dep.target_id,
            weight=dep.weight,
            description=dep.description
        )

    return graph


def calculate_centrality(graph: nx.DiGraph) -> Dict[str, dict]:
    """
    Calculates multiple centrality metrics for each service node.

    Metrics calculated:
    - in_degree_centrality  : how many services depend on this one
                              (higher = more critical, more things will break if it fails)
    - betweenness_centrality: how often this node sits on the path between others
                              (higher = more of a bottleneck)
    - pagerank              : overall influence score in the network
                              (borrowed from Google's PageRank algorithm)

    Returns a dict: { service_id: { metric: value } }
    """
    in_degree   = nx.in_degree_centrality(graph)
    betweenness = nx.betweenness_centrality(graph, weight="weight")
    pagerank    = nx.pagerank(graph, weight="weight")

    results = {}
    for node in graph.nodes:
        results[node] = {
            "in_degree_centrality"  : round(in_degree.get(node, 0.0), 4),
            "betweenness_centrality": round(betweenness.get(node, 0.0), 4),
            "pagerank"              : round(pagerank.get(node, 0.0), 4),
            # combined centrality score — average of all three
            "combined_centrality"   : round(
                (in_degree.get(node, 0.0) +
                 betweenness.get(node, 0.0) +
                 pagerank.get(node, 0.0)) / 3,
                4
            )
        }

    return results


def get_dependents(graph: nx.DiGraph, service_id: str) -> List[str]:
    """
    Returns list of services that directly depend on the given service.
    These are the services immediately impacted if service_id fails.
    """
    # predecessors in a directed graph = nodes with edges pointing TO service_id
    return list(graph.predecessors(service_id))


def get_dependencies(graph: nx.DiGraph, service_id: str) -> List[str]:
    """
    Returns list of services that the given service depends on.
    These are the services that, if they fail, directly impact service_id.
    """
    return list(graph.successors(service_id))


def compute_and_save_risk_scores(graph: nx.DiGraph, services: List[Service]):
    """
    Computes centrality-based risk scores for all services
    and saves them to the database.

    Note: ML failure_risk will be added later by ml_model.py
    This sets the centrality_score and overall_risk based on graph alone.
    """
    centrality = calculate_centrality(graph)

    # build list of (service_id, combined_centrality) to rank
    scored = [
        (s.id, centrality[s.id]["combined_centrality"])
        for s in services
        if s.id in centrality
    ]

    # sort descending — highest centrality = rank 1
    scored.sort(key=lambda x: x[1], reverse=True)

    for rank, (service_id, combined_score) in enumerate(scored, start=1):
        risk_score = RiskScore(
            service_id=service_id,
            centrality_score=combined_score,
            failure_risk=0.0,        # ML model fills this later
            overall_risk=combined_score,  # will be updated after ML
            rank=rank
        )
        save_risk_score(risk_score)

    print(f"Risk scores computed and saved for {len(scored)} services.")


def build_and_analyze():
    """
    Main function — loads data from DB, builds graph,
    calculates centrality, saves risk scores.
    Call this on startup or when data changes.
    """
    services     = get_all_services()
    dependencies = get_all_dependencies()

    if not services:
        print("No services found. Run seed_data.py first.")
        return None

    graph = build_graph(services, dependencies)
    compute_and_save_risk_scores(graph, services)

    print(f"Graph built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    return graph


if __name__ == "__main__":
    build_and_analyze()
