"""
URL configuration for daissy-ai project.
"""

from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from ninja import NinjaAPI
from .api import api

# Create the main API instance
main_api = NinjaAPI(
    title="Audio Processing & Consultation Finder API",
    description="API for uploading, processing consultation audio files and helping users find relevant consultations",
    version="1.0.0"
)

# Add our API routes
main_api.add_router("/v1", api)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', main_api.urls),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)