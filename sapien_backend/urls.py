from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from core.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),
]
