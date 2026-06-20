# 💥 DepthCharge
### Microservice Dependency & Failure Risk Simulator

DepthCharge models how microservices depend on each other, simulates cascade failures when one service goes down, predicts which services are most likely to fail next using ML, and serves everything via a REST API.

---

## What it does

- **Dependency Mapping** — models which service depends on which, as a directed graph
- **Cascade Failure Simulation** — pick any service, simulate the domino effect across the network
- **Blast Radius Analysis** — instant preview of how many services are affected without full simulation
- **Critical Service Ranking** — ranks services by systemic importance using graph centrality (PageRank, betweenness, in-degree)
- **ML Failure Prediction** — Random Forest model predicts failure risk per service based on graph features and historical simulation data
- **Scheduled Retraining** — Airflow DAG retrains the model every night automatically

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Graph Engine | NetworkX |
| ML Model | scikit-learn (Random Forest) |
| REST API | FastAPI |
| Database | SQLite |
| Orchestration | Apache Airflow |
| Containerization | Docker |

---

## Project Structure

```
depthcharge/
├── models.py          # Core data classes — Service, Dependency, SimulationResult, RiskScore
├── database.py        # SQLite setup and all save/load operations
├── seed_data.py       # 12 fake ShopX microservices + dependencies for testing
├── network.py         # NetworkX graph builder + centrality score calculator
├── simulation.py      # Cascade failure simulation engine
├── ml_model.py        # Random Forest failure risk predictor
├── main.py            # FastAPI REST API
├── Dockerfile         # Docker containerization
├── requirements.txt   # Python dependencies
└── dags/
    └── retrain_dag.py # Airflow DAG for nightly retraining
```

---

## Quickstart

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/depthcharge.git
cd depthcharge
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Seed the database
```bash
python seed_data.py
```

### 4. Start the API
```bash
uvicorn main:app --reload
```

### 5. Open API docs
```
http://localhost:8000/docs
```

---

## Run with Docker

```bash
# build the image
docker build -t depthcharge .

# run the container
docker run -p 8000:8000 depthcharge

# open in browser
http://localhost:8000/docs
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | System health check |
| GET | `/services` | List all microservices |
| GET | `/services/{id}` | Get single service detail |
| GET | `/services/{id}/dependencies` | What it depends on and what depends on it |
| GET | `/metrics/critical-services` | All services ranked by criticality |
| GET | `/metrics/blast-radius/{id}` | Quick impact preview if service fails |
| POST | `/simulate/failure` | Run a cascade failure simulation |
| GET | `/simulate/history` | All past simulation runs |
| GET | `/simulate/{run_id}` | Get a specific simulation result |
| POST | `/ml/train` | Train the failure prediction model |
| GET | `/ml/predict` | Get ML failure risk scores for all services |
| POST | `/graph/analyze` | Rebuild graph and recalculate centrality |

---

## Example — Simulate a Failure

```bash
curl -X POST http://localhost:8000/simulate/failure \
  -H "Content-Type: application/json" \
  -d '{"service_id": "database-service"}'
```

Response:
```json
{
  "run_id": "abc-123",
  "triggered_by": "database-service",
  "failed_services": [
    "auth-service",
    "payment-service",
    "gateway-service",
    "order-service",
    "user-service"
  ],
  "cascade_depth": 3,
  "impact_score": 0.83,
  "timestamp": "2024-06-01T00:00:00"
}
```

---

## Airflow DAG

The `depthcharge_retrain` DAG runs every night at midnight:

```
rebuild_graph → retrain_model → log_summary
```

To run Airflow locally:
```bash
pip install apache-airflow
airflow db init
airflow webserver --port 8080
airflow scheduler
```

Place `dags/retrain_dag.py` in your Airflow `dags/` folder.

---

## Resume

> Built DepthCharge, a microservice dependency risk simulator modelling cascade failures across distributed systems using NetworkX graph analysis, scikit-learn Random Forest failure prediction, FastAPI REST API, SQLite, Docker containerization, and Apache Airflow for scheduled ML retraining.

---

## Author

Your Name — [GitHub](https://github.com/yourusername) · [LinkedIn](https://linkedin.com/in/yourprofile)
