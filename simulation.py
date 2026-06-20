"""
simulation.py
Core failure cascade simulation engine for DepthCharge.
Simulates what happens when one service fails — the domino effect.
"""

import uuid
from datetime import datetime
from typing import List, Set
import networkx as nx
from models import SimulationResult
from database import save_simulation_result, get_all_services


def simulate_failure(
    graph: nx.DiGraph,
    failed_service_id: str,
    failure_threshold: float = 0.5
) -> SimulationResult:
    """
    Simulates a cascade failure starting from one service.

    How it works:
    1. Mark the initial service as failed
    2. Find all services that depend on it (predecessors in graph)
    3. For each dependent — calculate how much of their total
       dependency weight is now gone
    4. If lost weight > failure_threshold (50% by default) → they fail too
    5. Repeat for newly failed services until no more failures spread

    Args:
        graph              : the NetworkX dependency graph
        failed_service_id  : the service that initially fails
        failure_threshold  : what fraction of dependency loss causes failure
                             0.5 = if 50% of what you depend on is gone, you fail

    Returns:
        SimulationResult with all failed services and impact metrics
    """

    if failed_service_id not in graph.nodes:
        raise ValueError(f"Service '{failed_service_id}' not found in graph")

    # track which services have failed
    failed: Set[str] = {failed_service_id}

    # track cascade depth — how many rounds of failures happened
    depth = 0

    # keep spreading until no new failures in a round
    changed = True
    while changed:
        changed = False
        depth += 1

        for node in graph.nodes:
            if node in failed:
                continue  # already failed, skip

            # get all services this node depends on
            dependencies = list(graph.successors(node))

            if not dependencies:
                continue  # no dependencies, cannot be impacted

            # calculate total dependency weight for this node
            total_weight = sum(
                graph[node][dep]["weight"]
                for dep in dependencies
            )

            if total_weight == 0:
                continue

            # calculate how much weight is lost due to failed dependencies
            lost_weight = sum(
                graph[node][dep]["weight"]
                for dep in dependencies
                if dep in failed
            )

            loss_ratio = lost_weight / total_weight

            # if loss ratio exceeds threshold — this service fails too
            if loss_ratio >= failure_threshold:
                failed.add(node)
                changed = True  # new failure found, keep going

    # remove the initially failed service from the cascade list
    # (it's the trigger, not a cascaded failure)
    cascaded = [s for s in failed if s != failed_service_id]

    # calculate impact score
    # = proportion of total services that went down
    total_services = graph.number_of_nodes()
    impact_score = round(len(failed) / total_services, 4)

    # build and save result
    result = SimulationResult(
        run_id=str(uuid.uuid4()),
        triggered_by=failed_service_id,
        failed_services=cascaded,
        cascade_depth=depth,
        impact_score=impact_score,
        timestamp=datetime.utcnow()
    )

    save_simulation_result(result)
    return result


def get_blast_radius(
    graph: nx.DiGraph,
    service_id: str
) -> dict:
    """
    Returns a quick summary of how many services would be
    directly and indirectly affected if this service fails.

    Direct   = services that immediately depend on this one
    Indirect = services reachable through the dependency chain

    Useful for a quick risk preview without running full simulation.
    """
    if service_id not in graph.nodes:
        raise ValueError(f"Service '{service_id}' not found in graph")

    # reverse the graph — follow dependency arrows backwards
    # to find who depends on this service
    reversed_graph = graph.reverse()

    # all nodes reachable from service_id in reversed graph
    # = all services that would be affected
    affected = nx.descendants(reversed_graph, service_id)

    direct   = set(reversed_graph.successors(service_id))
    indirect = affected - direct

    return {
        "service_id"      : service_id,
        "direct_impact"   : list(direct),
        "indirect_impact" : list(indirect),
        "total_affected"  : len(affected),
        "blast_radius_pct": round(len(affected) / graph.number_of_nodes() * 100, 1)
    }


if __name__ == "__main__":
    from database import get_all_services, get_all_dependencies
    from network import build_graph, build_and_analyze

    # build graph
    graph = build_and_analyze()

    if graph:
        # test simulation — what happens if database-service fails?
        print("\nSimulating failure of: database-service")
        result = simulate_failure(graph, "database-service")
        print(f"Failed services : {result.failed_services}")
        print(f"Cascade depth   : {result.cascade_depth}")
        print(f"Impact score    : {result.impact_score}")

        # blast radius preview
        print("\nBlast radius of: database-service")
        blast = get_blast_radius(graph, "database-service")
        print(f"Direct impact   : {blast['direct_impact']}")
        print(f"Indirect impact : {blast['indirect_impact']}")
        print(f"Total affected  : {blast['total_affected']} ({blast['blast_radius_pct']}%)")
