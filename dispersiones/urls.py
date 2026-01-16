from django.urls import path
from . import views

urlpatterns = [
    path('', views.dispersiones_lista, name='dispersiones_list'),
    path('kanban/', views.dispersiones_kanban, name='dispersiones_kanban'),
    path('kanban-ejecutivos/', views.dispersiones_kanban_ejecutivos, name='dispersiones_kanban_ejecutivos'),
    path('nueva/', views.agregar_dispersion, name='dispersiones_add'),
    path('editar/<int:id>/', views.editar_dispersion, name='dispersiones_edit'),
    path('eliminar/<int:id>/', views.eliminar_dispersion, name='dispersiones_delete'),
]
