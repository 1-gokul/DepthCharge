"""
models.py
Core data models for ServiceGraph — Microservice Dependency & Failure Risk Simulator
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Service:
    """
    Represents a single microservice in the system.
    
    Attributes:
        id          : unique identifier e.g. "auth-service"
        name        : human readable name e.g. "Authentication Service"
        team        : team responsible for this service
        criticality : manual importance tag — low / medium / high
        failure_rate: historical failure rate (0.0 to 1.0)
        is_active   : whether service is currently running
    """
    id: str
    name: str
    team: str
    criticality: str = "medium"       # low / medium / high
    failure_rate: float = 0.0         # historical failure rate 0.0 - 1.0
    is_active: bool = True

    def __post_init__(self):
        valid = ["low", "medium", "high"]
        if self.criticality not in valid:
            raise ValueError(f"criticality must be one of {valid}")
        if not (0.0 <= self.failure_rate <= 1.0):
            raise ValueError("failure_rate must be between 0.0 and 1.0")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "team": self.team,
            "criticality": self.criticality,
            "failure_rate": self.failure_rate,
            "is_active": self.is_active
        }


@dataclass
class Dependency:
    """
    Represents a directional dependency between two services.
    
    If service A depends on service B:
        source_id = A (the dependent)
        target_id = B (the one being depended on)
    
    Meaning: if B fails, A is directly impacted.

    Attributes:
        source_id  : service that depends on target
        target_id  : service being depended on
        weight     : strength of dependency (1=weak, 10=critical)
        description: what kind of dependency this is
    """
    source_id: str
    target_id: str
    weight: float = 1.0        # 1.0 (weak) to 10.0 (critical)
    description: str = ""

    def __post_init__(self):
        if self.source_id == self.target_id:
            raise ValueError("A service cannot depend on itself")
        if not (1.0 <= self.weight <= 10.0):
            raise ValueError("weight must be between 1.0 and 10.0")

    def to_dict(self):
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "weight": self.weight,
            "description": self.description
        }


@dataclass
class SimulationResult:
    """
    Stores the result of a single failure cascade simulation run.

    Attributes:
        run_id          : unique ID for this simulation run
        triggered_by    : which service was the initial failure
        failed_services : list of service IDs that went down as a result
        cascade_depth   : how many hops the failure spread
        impact_score    : overall impact score (0.0 to 1.0)
        timestamp       : when the simulation was run
    """
    run_id: str
    triggered_by: str
    failed_services: List[str] = field(default_factory=list)
    cascade_depth: int = 0
    impact_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "triggered_by": self.triggered_by,
            "failed_services": self.failed_services,
            "cascade_depth": self.cascade_depth,
            "impact_score": self.impact_score,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class RiskScore:
    """
    Represents a computed risk score for a service.
    Combines graph centrality + historical failure rate + ML prediction.

    Attributes:
        service_id      : which service this score belongs to
        centrality_score: NetworkX centrality value (0.0 to 1.0)
        failure_risk    : ML predicted failure probability (0.0 to 1.0)
        overall_risk    : combined final risk score (0.0 to 1.0)
        rank            : rank among all services (1 = highest risk)
    """
    service_id: str
    centrality_score: float = 0.0
    failure_risk: float = 0.0
    overall_risk: float = 0.0
    rank: Optional[int] = None

    def to_dict(self):
        return {
            "service_id": self.service_id,
            "centrality_score": round(self.centrality_score, 4),
            "failure_risk": round(self.failure_risk, 4),
            "overall_risk": round(self.overall_risk, 4),
            "rank": self.rank
        }
