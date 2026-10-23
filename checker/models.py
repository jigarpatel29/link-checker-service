from django.db import models


class Batch(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Batch {self.id}"

    @property
    def total(self):
        return self.urls.count()

    @property
    def completed(self):
        return self.urls.filter(checked_at__isnull=False).count()

    @property
    def status(self):
        if self.completed == 0:
            return "pending"
        if self.completed < self.total:
            return "in_progress"
        return "done"


class URLCheck(models.Model):
    batch = models.ForeignKey(
        Batch,
        related_name="urls",
        on_delete=models.CASCADE,
    )
    url = models.URLField(max_length=2048)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    final_url = models.URLField(max_length=2048, null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    last_check_failed = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.url
