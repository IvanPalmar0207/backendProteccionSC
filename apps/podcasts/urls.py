"""Podcast routes (mounted at /api/podcasts/)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PodcastViewSet

router = DefaultRouter()
router.register("", PodcastViewSet, basename="podcast")

urlpatterns = [path("", include(router.urls))]
