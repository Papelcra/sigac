from django.urls import path
from . import views
from users import views as user_views


urlpatterns = [
    path('cartelera/', views.movie_list, name='movie_list'),
    path('funcion/<int:show_id>/asientos/', views.seat_selection, name='seat_selection'),
    path('funcion/<int:show_id>/reservar/', views.reserve_seats, name='reserve_seats'),

    path('reservas-pendientes/', views.pending_reservations, name='pending_reservations'),
    path('confirmar-venta/<int:show_seat_id>/', views.confirm_sale, name='confirm_sale'),

    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<int:ticket_id>/pdf/', views.download_ticket_pdf, name='download_ticket_pdf'),

    path('validar-entrada/', views.validate_ticket, name='validate_ticket'),
    path('cierre-caja/', views.cierre_caja, name='cierre_caja'),

    # PANEL ADMIN PRODUCTOS
    
    path('panel/productos/', views.admin_productos, name='admin_productos'),
    path('panel/productos/nuevo/', views.crear_producto, name='crear_producto'),
    path('panel/productos/editar/<int:id>/', views.editar_producto, name='editar_producto'),
    path('panel/productos/eliminar/<int:id>/', views.eliminar_producto, name='eliminar_producto'),

    # PANEL ADMIN COMBOS
    path('panel/combos/', views.admin_combos, name='admin_combos'),
    path('panel/combos/nuevo/', views.crear_combo, name='crear_combo'),
    path('panel/combos/editar/<int:id>/', views.editar_combo, name='editar_combo'),
    path('panel/combos/eliminar/<int:id>/', views.eliminar_combo, name='eliminar_combo'),

    # PANEL VENDEDOR
    path("comprar-combo/<int:combo_id>/", user_views.comprar_combo, name="comprar_combo"),
    path('vender-producto/<int:id>/', views.vender_producto, name='vender_producto'),
    path('vender-combo/<int:id>/', views.vender_combo, name='vender_combo'),
]