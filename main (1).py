"""
main.py
FastAPI REST API for DepthCharge.
All endpoints to interact with the service graph, run simulations,
get risk scores, and failure predictions.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager

from database import (
    init_db,
    get_all_services,
    get_service,
    get_all_dependencies,
    get_dependencies_for_service,
    get_all_risk_scores,
    get_simulation_result,
    get_all_simulation_results
)
from network import build_graph, calculate_centrality, get_dependents, get_dependencies, build_and_analyze
from simulation import simulate_failure, get_blast_radius
from ml_model import train_model, predict_failure_risk


# ──────────────────────────────────────────────
# App startup — build graph once on launch
# ──────────────────────────────────────────────

graph = None
centrality = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph, centrality
    init_db()
    services     = get_all_services()
    dependencies = get_all_dependencies()
    if services:
        graph      = build_graph(services, dependencies)
        centrality = calculate_centrality(graph)
        print("Graph loaded on startup.")
    yield


app = FastAPI(
    title="DepthCharge API",
    description="Microservice Dependency & Failure Risk Simulator",
    version="1.0.0",
    lifespan=lifespan
)


# ──────────────────────────────────────────────
# Request bodies
# ──────────────────────────────────────────────

class SimulateRequest(BaseModel):
    service_id: str
    failure_threshold: Optional[float] = 0.5


class TrainRequest(BaseModel):
    retrain: bool = True


# ──────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "project" : "DepthCharge",
        "status"  : "running",
        "version" : "1.0.0"
    }


@app.get("/health")
def health():
    services = get_all_services()
    return {
        "status"          : "healthy",
        "total_services"  : len(services),
        "graph_loaded"    : graph is not None
    }


# ──────────────────────────────────────────────
# Services
# ──────────────────────────────────────────────

@app.get("/services")
def list_services():
    """Returns all microservices in the system."""
    services = get_all_services()
    return {"total": len(services), "services": [s.to_dict() for s in services]}


@app.get("/services/{service_id}")
def get_service_detail(service_id: str):
    """Returns details of a single service."""
    service = get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")
    return service.to_dict()


@app.get("/services/{service_id}/dependencies")
def service_dependencies(service_id: str):
    """
    Returns what this service depends on
    and what depends on this service.
    """
    if not get_service(service_id):
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found")

    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not loaded yet")

    depends_on  = get_dependencies(graph, service_id)   # what it needs
    depended_by = get_dependents(graph, service_id)      # what needs it

    return {
        "service_id"  : service_id,
        "depends_on"  : depends_on,
        "depended_by" : depended_by
    }


# ──────────────────────────────────────────────
# Risk & Metrics
# ──────────────────────────────────────────────

@app.get("/metrics/critical-services")
def critical_services():
    """
    Returns all services ranked by criticality.
    Rank 1 = most critical (highest risk if it fails).
    """
    scores = get_all_risk_scores()
    if not scores:
        return {"message": "No risk scores yet. Run /graph/analyze first."}
    return {
        "total"   : len(scores),
        "ranking" : [s.to_dict() for s in scores]
    }


@app.get("/metrics/blast-radius/{service_id}")
def blast_radius(service_id: str):
    """
    Returns how many services would be directly and indirectly
    affected if this service fails — without running a full simulation.
    """
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    try:
        return get_blast_radius(graph, service_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ──────────────────────────────────────────────
# Simulation
# ──────────────────────────────────────────────

@app.post("/simulate/failure")
def run_simulation(request: SimulateRequest):
    """
    Simulates a cascade failure starting from the given service.
    Returns which services failed and the overall impact score.
    """
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")

    try:
        result = simulate_failure(
            graph,
            request.service_id,
            request.failure_threshold
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/simulate/history")
def simulation_history():
    """Returns all past simulation runs."""
    results = get_all_simulation_results()
    return {
        "total"   : len(results),
        "history" : [r.to_dict() for r in results]
    }


@app.get("/simulate/{run_id}")
def get_simulation(run_id: str):
    """Returns result of a specific simulation run by ID."""
    result = get_simulation_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found")
    return result.to_dict()


# ──────────────────────────────────────────────
# ML Prediction
# ──────────────────────────────────────────────

@app.post("/ml/train")
def train(request: TrainRequest):
    """
    Trains (or retrains) the Random Forest failure prediction model
    using current graph features and simulation history.
    """
    if graph is None or centrality is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    train_model(graph, centrality)
    return {"message": "Model trained successfully"}


@app.get("/ml/predict")
def predict():
    """
    Returns ML-predicted failure risk scores for all services.
    Higher score = more likely to fail.
    """
    if graph is None or centrality is None:
        raise HTTPException(status_code=503, detail="Graph not loaded")
    predictions = predict_failure_risk(graph, centrality)
    if not predictions:
        return {"message": "No model found. Call POST /ml/train first."}
    return {"predictions": predictions}


# ──────────────────────────────────────────────
# Graph management
# ──────────────────────────────────────────────

@app.post("/graph/analyze")
def analyze_graph():
    """
    Rebuilds the graph and recalculates all centrality scores.
    Call this after adding new services or dependencies.
    """
    global graph, centrality
    services     = get_all_services()
    dependencies = get_all_dependencies()

    if not services:
        raise HTTPException(status_code=400, detail="No services found. Run seed_data.py first.")

    graph      = build_graph(services, dependencies)
    centrality = calculate_centrality(graph)
    build_and_analyze()

    return {
        "message" : "Graph analyzed successfully",
        "nodes"   : graph.number_of_nodes(),
        "edges"   : graph.number_of_edges()
    }
