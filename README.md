# IsoLogAI

An AI-powered Log Ingestion, Storage, and Real-time Anomaly Detection system built with Django, Django Rest Framework, Celery, Redis Streams, and scikit-learn.

## System Architecture

1. **Log Ingestion & Storage (`apps/logs`)**: Receives raw log entries via REST endpoint, persists them in the database, and adds them to a Redis Stream (`log-stream`).
2. **ML Pipeline (`apps/detection`)**: Features a thread-safe singleton manager loading an Isolation Forest model, transforms raw text & metadata into numerical vectors, and detects anomalous log structures.
3. **Anomaly Storage (`apps/anomalies`)**: Stores anomaly ratings, confidence scores, and links to the relevant log entries.
4. **Celery & Redis Streams**: Decoupled task workers handling ingestion stream consumption (`XREADGROUP`) and asynchronous model retraining.

## Project Structure

- `config/`: Root settings, WSGI/ASGI configurations, and Celery app setup.
- `apps/`: Modularized Django applications (`logs`, `anomalies`, `detection`).
- `docker/`: Docker container profiles and start files.
- `scripts/`: Simulation scripts for generating log logs and validating message flows.
- `requirements/`: Grouped lists of package dependencies.

## Local Development Setup

1. Create a python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
2. Install local developer requirements:
   ```bash
   pip install -r requirements/local.txt
   ```
3. Apply database migrations:
   ```bash
   python manage.py migrate
   ```
4. Run Django local development server:
   ```bash
   python manage.py runserver
   ```
5. Launch Celery Worker:
   ```bash
   celery -A config worker --loglevel=info
   ```
------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------


# IsoLogAI

Real-time log anomaly detection system. Ingests application logs, streams them through Redis, and scores each entry for anomalies using an Isolation Forest model — end to end, asynchronously, with no manual intervention.

## Stack

| Layer | Technology |
|---|---|
| API | Django + Django REST Framework |
| Streaming | Redis Streams |
| Async processing | Celery (worker + beat) |
| Anomaly detection | Isolation Forest (scikit-learn) |
| Database | PostgreSQL |
| Containerization | Docker Compose |

## Architecture

```
┌─────────────┐     POST /api/logs/      ┌──────────────┐
│   Client /   │ ───────────────────────▶ │   Django API │
│   Service    │                          │   (DRF)      │
└─────────────┘                          └──────┬───────┘
                                                  │ save
                                                  ▼
                                          ┌──────────────┐
                                          │  PostgreSQL  │
                                          │  (LogEntry)  │
                                          └──────┬───────┘
                                                  │ post_save signal
                                                  │ (on_commit)
                                                  ▼
                                          ┌──────────────┐
                                          │ Redis Stream │
                                          │ "log-stream" │
                                          │   (DB 1)     │
                                          └──────┬───────┘
                                                  │ XREADGROUP
                                                  │ (every 5s, via Celery Beat)
                                                  ▼
                                          ┌──────────────┐
                                          │ Celery Worker│
                                          │  consumer    │
                                          └──────┬───────┘
                                                  │ feature extraction
                                                  ▼
                                          ┌──────────────┐
                                          │  Isolation   │
                                          │   Forest     │
                                          │ (ModelManager)│
                                          └──────┬───────┘
                                                  │ score + is_anomaly
                                                  ▼
                                          ┌──────────────┐
                                          │  PostgreSQL  │
                                          │  (Anomaly)   │
                                          └──────────────┘
```

## Flow

1. A log is submitted via `POST /api/logs/` and persisted as a `LogEntry`.
2. A `post_save` signal (wrapped in `transaction.on_commit`) pushes the entry to a Redis Stream (`log-stream`, DB 1) via `XADD`.
3. Celery Beat triggers the `consume_stream` task every 5 seconds.
4. The Celery worker reads pending entries from the stream via a consumer group (`detection-group`) using `XREADGROUP`, extracts features, and scores each entry with a cached Isolation Forest model (thread-safe singleton via `ModelManager`).
5. Results are stored as `Anomaly` records linked to the original `LogEntry`, and the stream message is acknowledged (`XACK`).

## Project structure

```
config/          settings, WSGI/ASGI, Celery app (celery.py)
apps/
  logs/          ingestion API, LogEntry model, signals, Redis producer
  detection/     consumer, feature extraction, Isolation Forest, ModelManager, Celery tasks
  anomalies/     Anomaly model, list/filter API, stats endpoint
docker/          docker-compose.yml, docker-compose.override.yml, Dockerfile, entrypoint.sh
scripts/         synthetic log generation, stream testing helpers
requirements/
```

## Running locally

```bash
cd docker
docker-compose -p isologai up -d
```

Confirm all five containers are up:
```bash
docker ps
```
Expect `isologai-web-1`, `isologai-redis-1`, `isologai-celery_worker-1`, `isologai-celery_beat-1`, `isologai-db-1`, all `Up`.

## Verifying the pipeline end to end

Redis runs on **DB 1** in this project (`REDIS_URL=redis://redis:6379/1`) — `redis-cli` defaults to DB 0, so always pass `-n 1` when inspecting the stream manually.

```bash
# Confirm entries are landing in the stream
docker exec -it isologai-redis-1 redis-cli -n 1 XRANGE log-stream - +

# Confirm the consumer group is active and caught up
docker exec -it isologai-redis-1 redis-cli -n 1 XINFO GROUPS log-stream
# Healthy output looks like: pending: 0, lag: 0

# Confirm anomalies were actually scored
docker exec -it isologai-web-1 python manage.py shell -c \
  "from apps.anomalies.models import Anomaly; print(list(Anomaly.objects.all().values('id','log_entry_id','score','is_anomaly')))"
```

## Known issues / open items

- Each `LogEntry` currently triggers `push_log_to_stream` twice (harmless — the consumer dedupes via `hasattr(log_entry, 'anomaly')` — but root cause not yet confirmed; suspected Django dev-server autoreloader double-registering the signal in `apps.py`'s `ready()`).
- `pytest` / `pytest-django` are used for tests but not yet pinned in `requirements/`.

See `myreference.txt` for a detailed log of the Docker/Redis/Celery debugging process this project went through — worth a read if you hit similar "the code looks right but nothing's happening" symptoms.