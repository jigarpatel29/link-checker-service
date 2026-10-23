import time
from datetime import timedelta

import requests
from celery import shared_task
from django.utils import timezone

from .models import URLCheck


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=5,
)
def check_url(self, url_check_id):
    try:
        item = URLCheck.objects.get(id=url_check_id)
    except URLCheck.DoesNotExist:
        return

    started = time.monotonic()

    try:
        response = requests.get(
            item.url,
            timeout=(3, 7),
            allow_redirects=True,
            headers={"User-Agent": "LinkChecker/1.0"},
        )

        item.status_code = response.status_code
        item.response_time_ms = round(
            (time.monotonic() - started) * 1000
        )
        item.final_url = response.url
        item.error = None
        item.last_check_failed = response.status_code >= 400

    except requests.RequestException as exc:
        item.status_code = None
        item.response_time_ms = round(
            (time.monotonic() - started) * 1000
        )
        item.final_url = None
        item.error = str(exc)[:1000]
        item.last_check_failed = True

    item.checked_at = timezone.now()
    item.save()


@shared_task
def retry_failed_urls():
    cutoff = timezone.now() - timedelta(hours=1)

    failed_urls = URLCheck.objects.filter(
        last_check_failed=True,
        checked_at__lt=cutoff,
    )

    queued = 0

    for item in failed_urls.iterator():
        check_url.delay(item.id)
        queued += 1

    return queued
