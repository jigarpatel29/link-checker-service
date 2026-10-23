import random
import time

from django.db import transaction
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Batch, URLCheck
from .serializers import BatchCreateSerializer, BatchSerializer
from .tasks import check_url


class BatchListCreateView(APIView):
    def post(self, request):
        serializer = BatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            batch = Batch.objects.create()

            checks = [
                URLCheck(batch=batch, url=url)
                for url in serializer.validated_data["urls"]
            ]
            URLCheck.objects.bulk_create(checks)

            check_ids = list(
                batch.urls.values_list("id", flat=True)
            )

            transaction.on_commit(
                lambda: [
                    check_url.delay(check_id)
                    for check_id in check_ids
                ]
            )

        return Response(
            {"id": batch.id, "status": "pending"},
            status=status.HTTP_201_CREATED,
        )


class BatchDetailView(APIView):
    def get(self, request, pk):
        try:
            batch = Batch.objects.get(pk=pk)
        except Batch.DoesNotExist:
            return Response(
                {"error": "Batch not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(BatchSerializer(batch).data)


def fake_site(request):
    time.sleep(random.uniform(0, 5))

    if random.random() < 0.30:
        return HttpResponse(
            "Simulated server error",
            status=500,
        )

    return HttpResponse("Fake site is working", status=200)
