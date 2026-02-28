from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    CustomLoginView,
    admin_dashboard,
    cajero_dashboard,
    vendedor_dashboard,
    vigilante_dashboard,
    cliente_dashboard,
    home,
)

urlpatterns = [
    path('', home, name='home'),
    # Autenticación
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # Dashboards por rol
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('cajero-dashboard/', cajero_dashboard, name='cajero_dashboard'),
    path('vendedor-dashboard/', vendedor_dashboard, name='vendedor_dashboard'),
    path('vigilante-dashboard/', vigilante_dashboard, name='vigilante_dashboard'),
    path('cliente-dashboard/', cliente_dashboard, name='cliente_dashboard'),
]