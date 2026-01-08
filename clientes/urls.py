from django.urls import path
from . import views

urlpatterns = [
    path('', views.clientes_lista, name='clientes_list'),
    path('nuevo/', views.agregar_cliente, name='clientes_add'),
    path('editar/<int:id>/', views.editar_cliente, name='clientes_edit'),
    path('eliminar/<int:id>/', views.eliminar_cliente, name='clientes_delete'),
]
