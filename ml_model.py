"""
ml_model.py
Random Forest failure risk predictor for DepthCharge.
Trains on graph features + historical failure data to predict
which services are most likely to fail next.
"""

import os
import pickle
import numpy as np
from typing import List, Dict
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

import networkx as nx
from models import RiskScore
from database import (
    get_all_services,
    get_all_dependencies,
    get_all_simulation_results,
    get_all_risk_scores,
    save_risk_score
)
from network import build_graph, calculate_centrality

MODEL_PATH = "depthcharge_model.pkl"
SCALER_PATH = "depthcharge_scaler.pkl"


def extract_features(
    graph: nx.DiGraph,
    centrality: Dict[str, dict]
) -> Dict[str, List[float]]:
    """
    Extracts ML features for each service from the graph.

    Features per service:
    1. in_degree_centrality   — how many services depend on it
    2. betweenness_centrality — how much of a bottleneck it is
    3. pagerank               — overall influence in network
    4. out_degree             — how many services it depends on
    5. in_degree              — raw count of dependents
    6. failure_rate           — historical failure rate from seed data

    Returns dict: { service_id: [f1, f2, f3, f4, f5, f6] }
    """
    services = get_all_services()
    service_map = {s.id: s for s in services}

    features = {}
    for node in graph.nodes:
        c = centrality.get(node, {})
        service = service_map.get(node)
        features[node] = [
            c.get("in_degree_centrality", 0.0),
            c.get("betweenness_centrality", 0.0),
            c.get("pagerank", 0.0),
            graph.out_degree(node),         # number of things it depends on
            graph.in_degree(node),          # number of things depending on it
            service.failure_rate if service else 0.0
        ]

    return features


def build_training_data(
    graph: nx.DiGraph,
    centrality: Dict[str, dict]
):
    """
    Builds training data from simulation history.

    Label = 1 if a service appeared in failed_services in any simulation
    Label = 0 if it never failed in any simulation

    If no simulation history exists, generates synthetic labels
    based on failure_rate thresholds (for cold start).
    """
    features = extract_features(graph, centrality)
    services = get_all_services()
    simulation_results = get_all_simulation_results()

    # collect all services that have appeared as failed
    historically_failed = set()
    for result in simulation_results:
        historically_failed.update(result.failed_services)
        historically_failed.add(result.triggered_by)

    X = []
    y = []
    service_ids = []

    for service in services:
        if service.id not in features:
            continue

        X.append(features[service.id])
        service_ids.append(service.id)

        if historically_failed:
            # use real simulation history
            label = 1 if service.id in historically_failed else 0
        else:
            # cold start — use failure_rate as proxy
            # services with failure_rate > 0.07 labeled as high risk
            label = 1 if service.failure_rate > 0.07 else 0

        y.append(label)

    return np.array(X), np.array(y), service_ids


def train_model(graph: nx.DiGraph, centrality: Dict[str, dict]):
    """
    Trains the Random Forest model and saves it to disk.
    Also updates risk scores in the database with ML predictions.
    """
    X, y, service_ids = build_training_data(graph, centrality)

    if len(X) < 4:
        print("Not enough data to train. Run more simulations first.")
        return

    # scale features to 0-1 range
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    # train/test split — only if enough samples
    if len(X) >= 8:
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
    else:
        # too few samples — train on all
        X_train, y_train = X_scaled, y
        X_test, y_test = X_scaled, y

    # train Random Forest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=4,
        random_state=42
    )
    model.fit(X_train, y_train)

    # evaluate
    y_pred = model.predict(X_test)
    print("\nModel Performance:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # save model and scaler
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    print(f"Model saved to {MODEL_PATH}")

    # update risk scores with ML predictions
    update_risk_scores_with_ml(model, scaler, X_scaled, service_ids, graph, centrality)


def update_risk_scores_with_ml(
    model,
    scaler,
    X_scaled,
    service_ids,
    graph,
    centrality
):
    """
    Uses the trained model to predict failure probabilities
    and updates risk scores in the database.

    overall_risk = 60% ML prediction + 40% centrality score
    """
    probabilities = model.predict_proba(X_scaled)

    # get probability of class 1 (failure)
    failure_probs = probabilities[:, 1] if probabilities.shape[1] > 1 else probabilities[:, 0]

    scored = []
    for i, service_id in enumerate(service_ids):
        c = centrality.get(service_id, {})
        centrality_score = c.get("combined_centrality", 0.0)
        failure_risk = round(float(failure_probs[i]), 4)

        # combined overall risk
        overall_risk = round(0.6 * failure_risk + 0.4 * centrality_score, 4)

        scored.append((service_id, centrality_score, failure_risk, overall_risk))

    # rank by overall_risk descending
    scored.sort(key=lambda x: x[3], reverse=True)

    for rank, (service_id, centrality_score, failure_risk, overall_risk) in enumerate(scored, start=1):
        risk_score = RiskScore(
            service_id=service_id,
            centrality_score=centrality_score,
            failure_risk=failure_risk,
            overall_risk=overall_risk,
            rank=rank
        )
        save_risk_score(risk_score)

    print(f"Risk scores updated with ML predictions for {len(scored)} services.")


def predict_failure_risk(graph: nx.DiGraph, centrality: Dict[str, dict]) -> List[dict]:
    """
    Loads saved model and returns failure risk predictions
    for all services, ranked by overall risk.
    """
    if not os.path.exists(MODEL_PATH):
        print("No trained model found. Run train_model() first.")
        return []

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)

    features = extract_features(graph, centrality)
    services = get_all_services()

    results = []
    for service in services:
        if service.id not in features:
            continue
        X = np.array([features[service.id]])
        X_scaled = scaler.transform(X)
        prob = model.predict_proba(X_scaled)[0]
        failure_risk = round(float(prob[1]) if len(prob) > 1 else float(prob[0]), 4)
        results.append({
            "service_id"  : service.id,
            "failure_risk": failure_risk
        })

    results.sort(key=lambda x: x["failure_risk"], reverse=True)
    return results


if __name__ == "__main__":
    from network import build_and_analyze, calculate_centrality
    from database import get_all_services, get_all_dependencies
    from network import build_graph

    services     = get_all_services()
    dependencies = get_all_dependencies()
    graph        = build_graph(services, dependencies)
    centrality   = calculate_centrality(graph)

    print("Training failure prediction model...")
    train_model(graph, centrality)

    print("\nTop failure risk predictions:")
    predictions = predict_failure_risk(graph, centrality)
    for p in predictions:
        print(f"  {p['service_id']:<30} risk: {p['failure_risk']}")
