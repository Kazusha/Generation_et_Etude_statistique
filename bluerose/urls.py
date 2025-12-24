from django.urls import path
from bluerose import views

urlpatterns = [
    path('', views.dashboard),                 # accueil = Dashboard
    path('generer/', views.generer_page),
    path('importer/', views.importer_page),

    # API endpoints
    path('upload/', views.upload_csv),
    path('upload_user_csv/', views.upload_user_csv),
    path('stats/', views.stats),
    path('charts_data/', views.charts_data),
    path('export/', views.exporter_donnee),
]
