# Link Checker Service

A Django REST API that checks submitted URLs asynchronously using Celery, Redis, PostgreSQL, and Docker Compose.

## Features

- Submit a batch containing 1–100 HTTP/HTTPS URLs.
- Receive a batch ID without waiting for all URL checks to finish.
- Check batch progress and retrieve individual URL results.
- Record HTTP status code, response time, final URL after redirects, errors, and check timestamp.
- Recheck failed URLs hourly using Celery Beat.
- Provide a simulated endpoint that waits randomly and returns HTTP 500 approximately 30% of the time.
- Run the application and its dependencies using Docker Compose.

## Requirements

- Docker Desktop
- Docker Compose

No local Python installation is required because Python runs inside Docker.

## Setup

1. Clone this repository.
2. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and set your own Django secret key, PostgreSQL password, and Redis password. Ensure `REDIS_URL` contains the same Redis password as `REDIS_PASSWORD`.
4. Start the services:

   ```bash
   docker compose up --build -d
   ```

The application will be available at http://localhost:8000.

Docker Compose starts Django, PostgreSQL, Redis, a Celery worker, and Celery Beat. Database migrations are applied automatically when the web service starts.

## API

### 1. Submit a batch

**POST** `/batches/`

Example:

```bash
curl -X POST http://localhost:8000/batches/ \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://example.com","https://example.org"]}'
```

Example response:

```json
{
  "id": 1,
  "status": "pending"
}
```

Submit between 1 and 100 valid HTTP/HTTPS URLs. Invalid input returns HTTP 400 with validation details.

### 2. Retrieve batch results

**GET** `/batches/<id>/`

Example:

```bash
curl http://localhost:8000/batches/1/
```

The response includes the batch status (`pending`, `in_progress`, or `done`), progress counts, and the results for each URL.

Each result includes the submitted URL, HTTP status code, response time in milliseconds, final URL, error information, and check timestamp.

### 3. Simulated flaky website

**GET** `/fake-site/`

Example:

```bash
curl -i http://localhost:8000/fake-site/
```

The endpoint waits for a random duration between 0 and 5 seconds, then returns HTTP 500 approximately 30% of the time and HTTP 200 otherwise.

## Background processing

- Celery workers execute URL checks asynchronously.
- Redis acts as the Celery message broker.
- PostgreSQL stores batches, URL records, and check results.
- Celery Beat schedules failed URL checks to be retried hourly.

## Running tests

Run the automated tests with:

```bash
docker compose exec web python manage.py test checker
```

## Useful commands

Check service status:

```bash
docker compose ps
```

View worker logs:

```bash
docker compose logs --tail=100 worker
```

View scheduler logs:

```bash
docker compose logs --tail=100 beat
```

Stop services:

```bash
docker compose down
```

PostgreSQL data is stored in a Docker volume and persists when services are stopped. To remove the database volume as well, use `docker compose down -v`; this permanently deletes the persisted database data.

## Security

- Never commit `.env` or real credentials.
- Use strong, unique passwords and a generated Django secret key.
- `.env.example` contains placeholders for local setup.

## Design decisions

See [DECISIONS.md](DECISIONS.md) for processing choices, failure handling, scaling considerations, and AI usage.

## AI usage

AI assistance was used to help scaffold the project, explain Django and Celery, and troubleshoot development issues. The implementation was tested and adjusted during development.

## Background Processing

The application uses Celery for asynchronous URL checking and Redis as its message broker.

Django creates a batch and its URL check records in PostgreSQL.

After the database transaction commits, Django queues one Celery task per URL check using check_url.delay(check_id).

Redis holds the pending task messages.

A Celery worker consumes each task, retrieves the URL check record from PostgreSQL, and sends an HTTP request.

The worker saves the HTTP status code, response time, final URL, error details, and check timestamp to PostgreSQL.

Celery Beat schedules retry_failed_urls to run hourly and enqueue previously failed checks that are due for another attempt.

PostgreSQL stores the application records and check results. Redis handles task messaging and is also configured as the Celery result backend.
