from urllib.parse import urlsplit

from rest_framework import serializers

from .models import Batch, URLCheck


class BatchCreateSerializer(serializers.Serializer):
    urls = serializers.ListField(
        child=serializers.URLField(max_length=2048),
        min_length=1,
        max_length=100,
    )

    def validate_urls(self, urls):
        for url in urls:
            parsed = urlsplit(url)

            if (
                parsed.scheme not in ("http", "https")
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise serializers.ValidationError(
                    f"Invalid HTTP/HTTPS URL: {url}"
                )

            try:
                parsed.port
            except ValueError:
                raise serializers.ValidationError(
                    f"Invalid port in URL: {url}"
                )

        return urls


class URLCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = URLCheck
        fields = [
            "url",
            "status_code",
            "response_time_ms",
            "final_url",
            "error",
            "checked_at",
        ]


class BatchSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    progress = serializers.SerializerMethodField()
    results = URLCheckSerializer(source="urls", many=True, read_only=True)

    class Meta:
        model = Batch
        fields = ["id", "status", "progress", "results"]

    def get_progress(self, obj):
        return {
            "completed": obj.completed,
            "total": obj.total,
        }