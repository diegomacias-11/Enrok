from django.urls import path
from . import views

urlpatterns = [
    path('', views.alianzas_lista, name='alianzas_list'),
    path('nueva/', views.agregar_alianza, name='alianzas_add'),
    path('editar/<int:id>/', views.editar_alianza, name='alianzas_edit'),
    path('eliminar/<int:id>/', views.eliminar_alianza, name='alianzas_delete'),
]
