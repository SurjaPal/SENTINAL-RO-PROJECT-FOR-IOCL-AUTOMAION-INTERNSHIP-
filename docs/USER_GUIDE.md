# Sentinel-RO: Local Setup & User Guide

This guide will walk you through setting up and running the Sentinel-RO project on a completely new system from scratch.

## 1. Prerequisites
Before you begin, ensure you have the following installed on your machine:
*   **[Docker Desktop](https://www.docker.com/products/docker-desktop/)**: Required to run the isolated microservices, databases, and message brokers. Ensure the Docker daemon is running.
*   **[Git](https://git-scm.com/downloads)**: To clone the repository.
*   *(Optional but recommended)* A code editor like **[VS Code](https://code.visualstudio.com/)** to view the source code.

## 2. Clone the Repository
Open your terminal (or Command Prompt/PowerShell) and clone the project:
```bash
git clone <your-repository-url>
cd sentinel-ro
```

## 3. Configure Environment Variables
The project requires a `.env` file to store sensitive configuration details, primarily the Google Gemini API Key used by the AI Assistant.

1.  In the root of the project, you will find a file named `.env.example`.
2.  Duplicate this file and rename the copy to `.env`.
    *   *Windows (Command Prompt):* `copy .env.example .env`
    *   *Mac/Linux:* `cp .env.example .env`
3.  Open the new `.env` file in your text editor.
4.  Locate the line `GEMINI_API_KEY=your_api_key_here` and replace the placeholder with your actual Google Gemini API Key. (You can generate one for free at [Google AI Studio](https://aistudio.google.com/)).

## 4. Start the Application Stack
Because the project is entirely containerized using Docker, you do not need to manually install Python, Node.js, PostgreSQL, or Kafka on your host machine. 

To build and start all services, you can either:

**Option A: Use the startup script (Windows)**
Simply double-click the `start-stack.bat` file in the root directory, or run it from the command line:
```cmd
.\start-stack.bat
```

**Option B: Use Docker Compose directly (Any OS)**
```bash
docker compose up -d --build
```
*Note: The first time you run this, it may take a few minutes to download the base images (PostgreSQL, Grafana, Node, Python) and build the containers.*

## 5. Access the Platforms
Once the terminal indicates that all containers are running, you can access the various parts of the system through your web browser:

*   **Sentinel-RO Web UI:** [http://localhost:8080](http://localhost:8080)
    *   *This is the main React dashboard where you can view live telemetry, automation insights, and chat with the AI Assistant.*
*   **Grafana Dashboard:** [http://localhost:3000](http://localhost:3000)
    *   *Login credentials:* Username: `admin`, Password: `sentinel`
    *   *This interface provides deep-dive historical metrics directly from the TimescaleDB database.*
*   **FastAPI Backend Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
    *   *Interactive documentation for the REST API.*

## 6. Testing the Simulation
The stack automatically starts a background `simulator` container. This simulator mimics physical IoT sensors at retail outlets and continuously pumps telemetry (temperature, fuel volume, simulated battery degradation) into the ingestion pipeline.

As long as the stack is running, data is flowing. You will see the metrics updating live on the Web UI, and you can query the historical data in Grafana.

## 7. Stopping the Application
When you are finished, you can safely shut down the entire stack without losing your database data.

Run the following command in your terminal:
```bash
docker compose down
```
*(If you want to completely wipe the database and start fresh next time, you can run `docker compose down -v` to remove the data volumes).*
