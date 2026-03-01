from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    CustomLoginView,
    home,
    admin_dashboard,
    cajero_dashboard,
    vendedor_dashboard,
    vigilante_dashboard,
    cliente_dashboard,
    # Vistas para películas (CRUD completo)
    admin_peliculas,admin_pelicula_crear,admin_pelicula_editar,admin_pelicula_eliminar,
    # Vistas para las otras secciones (puedes agregar más después)
    admin_funciones,admin_salas,admin_usuarios,
    admin_funcion_crear, admin_funcion_editar, admin_funcion_eliminar,admin_sala_crear,
    admin_sala_editar, admin_sala_eliminar,
    admin_usuario_crear, admin_usuario_editar, admin_usuario_eliminar,
    admin_reportes,export_reportes_pdf,
)

urlpatterns = [
    # Raíz (home que redirige según rol)
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

    # Secciones del rol admin (frontend, NO el admin de Django)
    # Películas - CRUD completo
    path('admin-peliculas/', admin_peliculas, name='admin_peliculas'),
    path('admin-peliculas/crear/', admin_pelicula_crear, name='admin_pelicula_crear'),
    path('admin-peliculas/editar/<int:pelicula_id>/', admin_pelicula_editar, name='admin_pelicula_editar'),
    path('admin-peliculas/eliminar/<int:pelicula_id>/', admin_pelicula_eliminar, name='admin_pelicula_eliminar'),

    # Otras secciones (placeholders por ahora - agrégalas cuando las tengas listas)
    path('admin-funciones/', admin_funciones, name='admin_funciones'),
    path('admin-salas/', admin_salas, name='admin_salas'),
    path('admin-usuarios/', admin_usuarios, name='admin_usuarios'),

    path('admin-funciones/crear/', admin_funcion_crear, name='admin_funcion_crear'),
    path('admin-funciones/editar/<int:funcion_id>/', admin_funcion_editar, name='admin_funcion_editar'),
    path('admin-funciones/eliminar/<int:funcion_id>/', admin_funcion_eliminar, name='admin_funcion_eliminar'),

    path('admin-salas/crear/', admin_sala_crear, name='admin_sala_crear'),
    path('admin-salas/editar/<int:sala_id>/', admin_sala_editar, name='admin_sala_editar'),
    path('admin-salas/eliminar/<int:sala_id>/', admin_sala_eliminar, name='admin_sala_eliminar'),

    path('admin-usuarios/crear/', admin_usuario_crear, name='admin_usuario_crear'),
    path('admin-usuarios/editar/<int:usuario_id>/', admin_usuario_editar, name='admin_usuario_editar'),
    path('admin-usuarios/eliminar/<int:usuario_id>/', admin_usuario_eliminar, name='admin_usuario_eliminar'),
    path('admin-reportes/', admin_reportes, name='admin_reportes'),
    path('admin-reportes/export-pdf/', export_reportes_pdf, name='export_reportes_pdf'),

]