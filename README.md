# Kafka Events System

This project is a small real-time event analytics platform built with Flask, Kafka, Spark Structured Streaming, and a lightweight sentiment analysis layer.

It collects social-style messages, publishes them to Kafka, processes them with Spark, and exposes the results through a web dashboard and documented API endpoints.

## What the project does

The system supports two ingestion modes:

- sample replay from a local JSONL file for demos and local testing
- live fetch from X API using a bearer token

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
- publishing sample or live X events into Kafka
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
- `POST /publish/x` fetch recent posts from X and publish them into Kafka
- `GET /api/openapi.json` OpenAPI specification
- `GET /api/docs` Swagger UI
- `GET /api/dashboard/summary` dashboard aggregate data
- `GET /api/dashboard/events` latest events visible to the dashboard

## Project flow

The normal execution flow is:

1. Start Zookeeper and Kafka locally
2. Start the Flask app
3. Start the Spark consumer
4. Publish events using either the sample route or the X route
5. Open the dashboard or Swagger UI in the browser

## Local setup

Requirements:

- Kafka running on `localhost:9092`
- Zookeeper running on `localhost:2181`
- Java installed for Spark

Use the local virtual environment already prepared in `.venv`.

### Train the optional ML model

```powershell
.\.venv\Scripts\python.exe -m ml.train_model
```

### Start the Flask app

```powershell
.\.venv\Scripts\python.exe app.py
```

### Start the Spark consumer

```powershell
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5 analytics\spark_consumer.py --kafka-bootstrap localhost:9092 --topic raw_posts --predictions-topic predictions
```

## Configuration

Configuration is loaded from `.env`.

Important variables:

- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_TOPIC_RAW`
- `KAFKA_TOPIC_PREDICTIONS`
- `X_BEARER_TOKEN`
- `X_QUERY`
- `X_SEARCH_MAX_RESULTS`
- `MODEL_PATH`

Use `.env.example` as the template.

## Notes

- If X API access is unavailable, the sample replay mode is enough to demonstrate the full pipeline.
- The trained model is optional. If it is missing, the system still works with lexicon sentiment only.
- A French project report is included in `report.md`.
