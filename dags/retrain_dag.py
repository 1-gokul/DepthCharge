"""
dags/retrain_dag.py
Airflow DAG for DepthCharge.
Runs every night at midnight to:
1. Rebuild the service dependency graph
2. Recalculate centrality scores
3. Retrain the Random Forest failure prediction model
4. Update risk scores in the database
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# make sure airflow can find our project files
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


# ──────────────────────────────────────────────
# Task functions
# ──────────────────────────────────────────────

def task_rebuild_graph():
    """
    Pulls latest services and dependencies from DB
    and rebuilds the NetworkX graph.
    Stores graph data for next tasks via XCom.
    """
    from database import get_all_services, get_all_dependencies
    from network import build_graph, calculate_centrality, compute_and_save_risk_scores

    print("Rebuilding service dependency graph...")
    services     = get_all_services()
    dependencies = get_all_dependencies()

    if not services:
        raise ValueError("No services found in database. Run seed_data.py first.")

    graph      = build_graph(services, dependencies)
    centrality = calculate_centrality(graph)
    compute_and_save_risk_scores(graph, services)

    print(f"Graph rebuilt: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    return "graph_built"


def task_retrain_model():
    """
    Retrains the Random Forest model on latest
    graph features and simulation history.
    Updates risk scores with new ML predictions.
    """
    from database import get_all_services, get_all_dependencies
    from network import build_graph, calculate_centrality
    from ml_model import train_model

    print("Retraining failure prediction model...")
    services     = get_all_services()
    dependencies = get_all_dependencies()
    graph        = build_graph(services, dependencies)
    centrality   = calculate_centrality(graph)

    train_model(graph, centrality)
    print("Model retrained and risk scores updated.")
    return "model_retrained"


def task_log_summary():
    """
    Logs a summary of current risk scores after retraining.
    Useful for monitoring — visible in Airflow task logs.
    """
    from database import get_all_risk_scores

    print("Current risk score summary after retraining:")
    print(f"{'Rank':<6} {'Service ID':<35} {'Overall Risk':<15}")
    print("-" * 56)

    scores = get_all_risk_scores()
    for score in scores:
        print(
            f"{score.rank:<6} "
            f"{score.service_id:<35} "
            f"{score.overall_risk:<15}"
        )

    print(f"\nTotal services scored: {len(scores)}")
    return "summary_logged"


# ──────────────────────────────────────────────
# DAG definition
# ──────────────────────────────────────────────

default_args = {
    "owner"           : "depthcharge",
    "depends_on_past" : False,
    "email_on_failure": False,
    "email_on_retry"  : False,
    "retries"         : 1,
    "retry_delay"     : timedelta(minutes=5),
}

with DAG(
    dag_id="depthcharge_retrain",
    description="Nightly graph rebuild and ML model retraining for DepthCharge",
    default_args=default_args,
    schedule_interval="0 0 * * *",   # every day at midnight
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["depthcharge", "ml", "retraining"],
) as dag:

    # Task 1 — rebuild graph and centrality scores
    rebuild_graph = PythonOperator(
        task_id="rebuild_graph",
        python_callable=task_rebuild_graph,
    )

    # Task 2 — retrain ML model
    retrain_model = PythonOperator(
        task_id="retrain_model",
        python_callable=task_retrain_model,
    )

    # Task 3 — log summary of new risk scores
    log_summary = PythonOperator(
        task_id="log_summary",
        python_callable=task_log_summary,
    )

    # Pipeline order: rebuild → retrain → log
    rebuild_graph >> retrain_model >> log_summary
