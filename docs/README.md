# Sentinel-RO 

An end-to-end predictive maintenance and analytics pipeline for retail fuel outlets, featuring live IoT ingestion, machine learning anomaly detection, and a Gemini-powered AI Assistant.

## Overview
Sentinel-RO mimics a real-world edge-to-cloud IoT architecture for fuel stations. It captures high-frequency telemetry from Automatic Tank Gauges (ATGs), Dispenser Units (DUs), and Power Supply Parameters (PSPs), processes this data through distributed analytics modules, and surfaces actionable insights to a React-based frontend and Grafana dashboard.

### Core Features
- **Real-time IoT Ingestion:** Simulates live telemetry over MQTT, bridging into Kafka (Redpanda) for high-throughput stream processing.
- **Predictive Fault Alerts (Module 1):** Uses Gradient Boosted Machine Learning to predict hardware failures hours before they occur based on battery and sensor degradation trajectories.
- **Reconciliation Anomaly Watch (Module 3):** Uses Isolation Forests and statistical baselines to catch unusual fuel variances (e.g., short deliveries or leaks) in near real-time.
- **Auto-Triage & RAG (Module 2):** Uses NLP to automatically classify operator complaints, cross-reference them against live hardware alarms, and suggest root causes.
- **Gemini AI Assistant:** A built-in AI copilot (powered by the Google Gemini API) with session memory, capable of answering operator questions about live system anomalies, tickets, and complaints.
- **Live Dashboards:** A fully responsive React/Tailwind web application powered by WebSockets, plus an integrated Grafana instance for deep-dive historical metrics.

## Technology Stack
- **Frontend:** React, Vite, TailwindCSS, Framer Motion, Lucide Icons
- **Backend API:** FastAPI (Python), WebSockets
- **Analytics & ML:** Pandas, Scikit-learn, Scipy, Google GenAI (Gemini 1.5)
- **Data Engineering:** Mosquitto (MQTT), Redpanda (Kafka), TimescaleDB (PostgreSQL)
- **Infrastructure:** Docker, Docker Compose

## Quick Start

### 1. Configuration
Copy the environment template and add your Gemini API Key.
```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_actual_key_here
```

### 2. Launch the Stack
You can start the entire infrastructure using the provided startup script, or run docker directly:
```bash
docker compose up -d --build
```
This will spin up the database, message brokers, ingestion pipelines, analytics engine, API backend, and the frontend web UI.

*Note: On the first boot, TimescaleDB will automatically run the schema migrations in the `schema/` directory.*

### 3. Access the Platforms
Once the containers are healthy, you can access the different interfaces:
- **Web UI & AI Assistant:** [http://localhost:8080](http://localhost:8080)
- **Grafana Dashboards:** [http://localhost:3000](http://localhost:3000) *(Login: admin / sentinel)*
- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

## Architecture Deep Dive

The project is structured into fully decoupled microservices:

1. **Simulator (`simulator/`)**: Generates realistic, high-frequency synthetic telemetry for testing, including intentionally injected anomalies and degradation curves.
2. **Ingestion Pipeline (`ingestion/`)**: 
   - `mqtt_to_kafka_bridge.py`: Consumes raw IoT messages from Mosquitto and publishes them to Kafka topics.
   - `kafka_to_timescale_sink.py`: Consumes Kafka streams and writes structured rows into TimescaleDB.
3. **Analytics Engine (`analytics/`)**:
   - Three distinct modules running batch analysis over the TimescaleDB history to generate predictive flags, detect anomalies, and triage complaints.
4. **Backend API (`api/`)**: A FastAPI server that exposes REST endpoints for the generated insights and a WebSocket endpoint for live 1.5s telemetry streaming to the UI. It also handles the orchestration of the Gemini AI chat.
5. **Web Interface (`web/`)**: A modern React application that visualizes the pipeline's output, rendering live telemetry cards, automation metrics, and hosting the chat UI.
6. **Grafana (`grafana/`)**: Pre-provisioned dashboards connecting directly to TimescaleDB for complex historical querying.

## Testing & Evaluation
The core logic for ingestion and the analytics modules is heavily unit-tested. You can run the test suite locally:
```bash
python -m unittest discover tests -v
```
To evaluate the specific accuracy of the ML models on synthetic data (Precision, Recall, F1 scores), you can run their respective evaluators:
```bash
python -m analytics.module1_fault_alerts.evaluate
python -m analytics.module3_anomaly_watch.evaluate
```
