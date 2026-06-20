# ──────────────────────────────────────────────
# Dockerfile for DepthCharge
# Microservice Dependency & Failure Risk Simulator
# ──────────────────────────────────────────────

# base image — lightweight Python
FROM python:3.11-slim

# set working directory inside container
WORKDIR /app

# copy requirements first (better caching)
COPY requirements.txt .

# install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# copy all project files
COPY . .

# seed the database on build
RUN python seed_data.py

# expose FastAPI port
EXPOSE 8000

# start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
