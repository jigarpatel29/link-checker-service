# Design Decisions

## 1. Synchronous vs. Asynchronous Processing

The API validates the submitted URLs, creates a batch and its URL records in PostgreSQL, and returns a batch ID without waiting for the checks to finish.

URL checks run asynchronously using Celery workers. This keeps API response times short even when URLs are slow or unresponsive.

Tasks are dispatched using Django's `transaction.on_commit()` so that workers do not attempt to process records before the database transaction commits.

## 2. Failure Handling, Retries, and Timeouts

HTTP requests use connection and read timeouts to prevent a slow website from occupying a worker indefinitely.

For each URL, the service records the HTTP status code, response time, final URL after redirects, error information, and check timestamp.

HTTP responses with status codes of 400 or higher are treated as failed checks. Request exceptions, including connection failures and timeouts, are also recorded as failures.

Celery Beat schedules `retry_failed_urls` every hour. The task queues URL records whose most recent check failed and whose last check was at least one hour ago.

The hourly scheduled retry is separate from immediate Celery task retries. The current implementation relies on the hourly task for rechecking failed URLs.

## 3. Handling Batches of 10,000 URLs

The API currently accepts up to 100 URLs per batch, as required by the assignment.

For batches of 10,000 URLs, I would make the following improvements:

- Dispatch work in chunks instead of creating thousands of individual queue messages inside the API request.
- Use Celery task groups or batches to distribute URL checks across workers.
- Apply per-host rate limits and concurrency controls to avoid overwhelming external websites.
- Add database indexes for frequently queried failure and timestamp fields.
- Paginate batch results to avoid returning thousands of records in one response.
- Monitor queue length, task latency, worker failures, and database performance.
- Consider request-level limits and backpressure to prevent queue overload.

These are scaling improvements for a larger workload; they are not all implemented in the current assignment.

## 4. Database and Queue Responsibilities

PostgreSQL stores batches, submitted URLs, and their check results persistently.

Redis acts as the Celery message broker, carrying background task messages between Django and Celery workers.

Celery Beat schedules recurring work, while Celery workers execute URL checks.

## 5. Docker and Configuration

Docker Compose runs Django, PostgreSQL, Redis, Celery workers, and Celery Beat as separate services.

Environment-specific values, including credentials and Django's secret key, are supplied through `.env`. The actual `.env` file is excluded from version control; `.env.example` documents the required configuration.

## 6. AI Usage

AI assistance was used to help scaffold the project, explain Django and Celery concepts, and troubleshoot implementation issues. The code and configuration were tested and adjusted during development. The final implementation should be reviewed and understood by the author before submission.
