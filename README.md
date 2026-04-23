# Kafka Events System

This project is a small real-time event analytics platform built with Flask, Kafka, Spark Structured Streaming, and a lightweight sentiment analysis layer.

It collects social-style messages, publishes them to Kafka, processes them with Spark, and exposes the results through a web dashboard and documented API endpoints.

## What the project does

The system supports two ingestion modes:

- sample replay from a local JSONL file for demos and local testing
- live fetch from Bluesky public search

Once messages are ingested:

1. Flask publishes raw events to the Kafka topic `raw_posts`
2. Spark Structured Streaming consumes the stream from Kafka
3. Spark enriches each event with:
   - lexicon-based sentiment
   - extracted hashtags
   - optional ML sentiment prediction if a trained model is available
4. Spark writes enriched events to the Kafka topic `predictions`
5. The dashboard reads recent Kafka messages and displays live metrics

## Main components

### Flask app

The Flask application is responsible for:

- serving the dashboard UI
- exposing API endpoints
- publishing sample or live Bluesky events into Kafka
- serving Swagger UI and the OpenAPI specification

### Kafka

Kafka acts as the event backbone of the system.

Topics used by default:

- `raw_posts`: raw incoming events
- `predictions`: processed and enriched events produced by Spark

### Spark Structured Streaming

Spark continuously reads Kafka events, parses them, enriches them, aggregates them, and republishes processed results.

The current processing includes:

- JSON parsing
- lexicon sentiment scoring
- sentiment labeling
- hashtag extraction
- windowed console aggregations
- optional ML sentiment inference

### Dashboard

The main dashboard is available at the root route `/`.

It displays:

- total recent events
- positive and negative ratios
- sentiment balance
- event rhythm over time
- top hashtags
- source breakdown
- latest processed messages

The dashboard reads the `predictions` topic first. If it is empty, it falls back to `raw_posts`.

### Swagger UI

Interactive API documentation is available through Swagger UI, which makes the endpoints easier to test from a browser.

## Available routes

- `GET /` live dashboard
- `GET /health` application health and runtime configuration summary
- `POST /publish/sample?limit=6&delay=1` publish sample events into Kafka
- `POST /publish/bluesky` fetch recent posts from Bluesky and publish them into Kafka
- `GET /api/openapi.json` OpenAPI specification
- `GET /api/docs` Swagger UI
- `GET /api/dashboard/summary` dashboard aggregate data
- `GET /api/dashboard/events` latest events visible to the dashboard

## Project flow

The normal execution flow is:

1. Start Zookeeper and Kafka on Windows
2. Start the Flask app on Windows
3. Start the Spark consumer from WSL
4. Publish events using either the sample route or the Bluesky route
5. Open the dashboard or Swagger UI in the browser

## Local setup

Requirements:

- Kafka running on `localhost:9092`
- Zookeeper running on `localhost:2181`
- Java installed for Spark
- Python 3.10+

### Windows environment for Flask

Create and activate a local virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### Train the optional ML model

```powershell
.\.venv\Scripts\python.exe -m ml.train_model
```

### Start the Flask app

```powershell
.\.venv\Scripts\python.exe app.py
```

### Start Zookeeper and Kafka on Windows

Use your local Kafka installation and start:

- Zookeeper on `localhost:2181`
- Kafka broker on `localhost:9092`

### WSL environment for Spark

The recommended Spark workflow is to run Spark from WSL instead of Windows.

Create the WSL virtual environment:

```bash
cd "/mnt/d/9raya/sem2/kafka events system"
python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Start the Spark consumer from WSL

Activate the WSL environment first:

```bash
cd "/mnt/d/9raya/sem2/kafka events system"
source .venv-wsl/bin/activate
```

Run Spark with local filesystem checkpoints to avoid HDFS requirements:

```bash
spark-submit \
  --conf spark.hadoop.fs.defaultFS=file:/// \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5 \
  analytics/spark_consumer.py \
  --kafka-bootstrap localhost:9092 \
  --topic raw_posts \
  --predictions-topic predictions \
  --checkpoint file:///tmp/kafka-events-checkpoints
```

When the consumer runs inside WSL, `analytics/spark_consumer.py` now rewrites `localhost:9092` to the Windows host IP from `/etc/resolv.conf`. That handles the common case where Kafka is started on Windows and Spark is started in WSL.

Important: Kafka must still advertise an address that WSL can reach. If your broker is configured with `advertised.listeners=PLAINTEXT://localhost:9092`, Spark may bootstrap successfully and then still fail after metadata lookup. In that case, configure the broker to advertise the Windows host IP or hostname that WSL can reach, for example:

```properties
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://192.168.x.x:9092
```

You can also pass that reachable address explicitly:

```bash
spark-submit \
  --conf spark.hadoop.fs.defaultFS=file:/// \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5 \
  analytics/spark_consumer.py \
  --kafka-bootstrap 192.168.x.x:9092 \
  --topic raw_posts \
  --predictions-topic predictions \
  --checkpoint file:///tmp/kafka-events-checkpoints
```

### Publish events into Kafka

After Flask and Spark are running, publish data through the API.

Sample replay:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:5000/publish/sample?limit=6&delay=1"
```

Bluesky search ingestion:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:5000/publish/bluesky"
```

### Open the app

```powershell
http://localhost:5000/
```

Swagger UI:

```powershell
http://localhost:5000/api/docs
```

## Configuration

Configuration is loaded from `.env`.

Important variables:

- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_TOPIC_RAW`
- `KAFKA_TOPIC_PREDICTIONS`
- `BLUESKY_API_BASE_URL`
- `BLUESKY_QUERY`
- `BLUESKY_SEARCH_LIMIT`
- `MODEL_PATH`

Use `.env.example` as the template.

For Bluesky search, use `https://api.bsky.app` as the API base URL. The older `https://public.api.bsky.app` host may return `403 Forbidden` for `app.bsky.feed.searchPosts` in some environments.

## Notes

- If Bluesky public search is rate-limited or unavailable, the sample replay mode is enough to demonstrate the full pipeline.
- The trained model is optional. If it is missing, the system still works with lexicon sentiment only.
- On Windows, running Spark directly may require extra Hadoop compatibility tooling. Running Spark from WSL is the recommended approach for this project.
- A French project report is included in `report.md`.
