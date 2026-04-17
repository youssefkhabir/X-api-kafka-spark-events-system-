# Kafka Events System

This project implements the TP pipeline requested in `TP_spark3.pdf`:

- collect posts from X or replay sample data
- publish events into Kafka
- consume and analyze the stream with Spark Structured Streaming
- compare a lexicon sentiment baseline with an optional ML model
- expose Swagger UI for API testing
- display a presentation-ready dashboard backed by Kafka data

## Architecture

`Flask app -> Kafka topic -> Spark Structured Streaming -> console aggregates / dashboard`

## Prerequisites

- Kafka running locally on `localhost:9092`
- Zookeeper running locally on `localhost:2181`
- Python 3.10+
- Java installed for Spark

## Install

```powershell
Copy-Item .env.example .env
```

The project-local environment has already been prepared in `.venv`. Use `.\.venv\Scripts\python.exe` for all commands below.

## Train the optional ML model

```powershell
.\.venv\Scripts\python.exe -m ml.train_model
```

## Start the Flask app

```powershell
.\.venv\Scripts\python.exe app.py
```

Available routes:

- `GET /` live dashboard
- `GET /health` app health and config summary
- `POST /publish/sample?limit=6&delay=1` replay sample posts into Kafka
- `POST /publish/x` fetch recent X posts and publish them into Kafka
- `GET /api/openapi.json` local OpenAPI specification
- `GET /api/docs` Swagger UI
- `GET /api/dashboard/summary` dashboard aggregates
- `GET /api/dashboard/events` latest dashboard-visible events

## Start the Spark consumer

```powershell
.\.venv\Scripts\python.exe analytics\spark_consumer.py --help
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5 analytics\spark_consumer.py --kafka-bootstrap localhost:9092 --topic raw_posts --predictions-topic predictions
```

If you trained the ML model first, the stream output will also include `ml_sentiment` and Spark will publish enriched records to the `predictions` topic.

## Notes

- If the X API access level does not allow recent search or the token is missing, use the sample replay route for the demo.
- The Spark script prints windowed sentiment counts and hashtag counts to the console.
- The dashboard reads the `predictions` topic first and falls back to `raw_posts` if Spark has not produced enriched data yet.
- The project report is available in `report.md` and is written in French.
