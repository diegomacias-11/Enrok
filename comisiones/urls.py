from django.urls import path
from . import views

urlpatterns = [
    path('', views.comisiones_lista, name='comisiones_list'),
    path('detalle/<int:comisionista_id>/', views.comisiones_detalle, name='comisiones_detail'),
    path('detalle/<int:comisionista_id>/enviar/', views.enviar_detalle_comisionista, name='comisiones_detail_send'),
    path('pago/nuevo/<int:comisionista_id>/', views.registrar_pago, name='comisiones_pago_add_by_id'),
    path('pago/nuevo/', views.registrar_pago, name='comisiones_pago_add'),
    path('pago/editar/<int:id>/', views.editar_pago, name='comisiones_pago_edit'),
    path('pago/eliminar/<int:id>/', views.eliminar_pago, name='comisiones_pago_delete'),
]
