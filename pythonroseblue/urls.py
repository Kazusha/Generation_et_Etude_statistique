from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("bluerose.urls")),  # inclut les routes de ton app
]
