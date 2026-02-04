from django.urls import path
from . import views

urlpatterns = [
    path('', views.dispersiones_servicios_lista, name='dispersiones_servicios_list'),
    path('kanban/', views.dispersiones_servicios_kanban, name='dispersiones_servicios_kanban'),
    path('kanban-contabilidad/', views.dispersiones_servicios_kanban_contabilidad, name='dispersiones_servicios_kanban_contabilidad'),
    path('nueva/', views.agregar_dispersion, name='dispersiones_servicios_add'),
    path('editar/<int:id>/', views.editar_dispersion, name='dispersiones_servicios_edit'),
    path('eliminar/<int:id>/', views.eliminar_dispersion, name='dispersiones_servicios_delete'),
]
