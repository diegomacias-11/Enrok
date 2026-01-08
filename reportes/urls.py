
from django.urls import path
from . import views

urlpatterns = [
    path('', views.reporte_looker, name='reportes_list'),
]
