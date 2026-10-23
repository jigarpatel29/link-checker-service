from django.contrib import admin
from django.urls import include, path
from checker.views import fake_site

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("checker.urls")),
    path("fake-site/", fake_site, name="fake-site"),
]
