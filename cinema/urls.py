from django.urls import path
from . import views

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
]