from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

# Modelos usados
from cinema.models import Movie, Show, Room, Ticket, ShowSeat
from .models import User  # comenta si usas el User default de Django
from .forms import MovieForm, ShowForm

# Vista raíz: redirige según rol
def home(request):
    if request.user.is_authenticated:
        role_redirects = {
            'admin': 'admin_dashboard',
            'cajero': 'cajero_dashboard',
            'vendedor': 'vendedor_dashboard',
            'vigilante': 'vigilante_dashboard',
            'cliente': 'cliente_dashboard',
        }
        dashboard = role_redirects.get(request.user.role)
        if dashboard:
            return redirect(dashboard)
        messages.warning(request, "Rol no reconocido.")
        return redirect('login')
    return redirect('login')


# Login personalizado
class CustomLoginView(LoginView):
    template_name = 'users/login.html'

    def get_success_url(self):
        role_redirects = {
            'admin': 'admin_dashboard',
            'cajero': 'cajero_dashboard',
            'vendedor': 'vendedor_dashboard',
            'vigilante': 'vigilante_dashboard',
            'cliente': 'cliente_dashboard',
        }
        return reverse_lazy(role_redirects.get(self.request.user.role, 'login'))


# Dashboards por rol
@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        messages.error(request, "Acceso no autorizado.")
        return redirect('home')

    today = timezone.now().date()
    context = {
        'total_peliculas': Movie.objects.count(),
        'funciones_hoy': Show.objects.filter(date=today, active=True).count(),
        'salas': Room.objects.all(),
        'ventas_dia': Ticket.objects.filter(purchase_date__date=today, status='paid').aggregate(total=Sum('price'))['total'] or 0,
    }
    return render(request, 'users/admin_dashboard.html', context)


@login_required
def cajero_dashboard(request):
    if request.user.role != 'cajero':
        messages.error(request, "Acceso no autorizado.")
        return redirect('home')

    today = timezone.now().date()
    boletos_hoy = Ticket.objects.filter(purchase_date__date=today, status='paid').count()
    total_hoy = Ticket.objects.filter(purchase_date__date=today, status='paid').aggregate(total=Sum('price'))['total'] or 0
    reservas_pendientes = ShowSeat.objects.filter(status='reservado').count()

    context = {
        'boletos_hoy': boletos_hoy,
        'total_hoy': total_hoy,
        'reservas_pendientes': reservas_pendientes,
        'today': today,
    }
    return render(request, 'users/cajero_dashboard.html', context)


@login_required
def vendedor_dashboard(request):
    if request.user.role != 'vendedor':
        messages.error(request, "Acceso no autorizado.")
        return redirect('home')
    return render(request, 'users/vendedor_dashboard.html')


@login_required
def vigilante_dashboard(request):
    if request.user.role != 'vigilante':
        messages.error(request, "Acceso no autorizado.")
        return redirect('home')
    return render(request, 'users/vigilante_dashboard.html')


@login_required
def cliente_dashboard(request):
    if request.user.role != 'cliente':
        messages.error(request, "Acceso no autorizado.")
        return redirect('home')

    tickets = Ticket.objects.filter(
        user=request.user,
        status__in=['paid', 'used']
    ).select_related(
        'show_seat__show__movie',
        'show_seat__seat'
    ).order_by('-purchase_date')

    context = {'tickets': tickets}
    return render(request, 'users/cliente_dashboard.html', context)


# Gestión de películas
@login_required
def admin_peliculas(request):
    if request.user.role != 'admin':
        messages.error(request, "Acceso solo para administradores.")
        return redirect('home')

    peliculas = Movie.objects.all().order_by('-release_date')
    return render(request, 'users/admin_peliculas.html', {'peliculas': peliculas})


@login_required
def admin_pelicula_crear(request):
    if request.user.role != 'admin':
        return redirect('home')

    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Película creada correctamente.")
            return redirect('admin_peliculas')
    else:
        form = MovieForm()

    return render(request, 'users/admin_pelicula_form.html', {'form': form, 'titulo': 'Crear Nueva Película'})


@login_required
def admin_pelicula_editar(request, pelicula_id):
    if request.user.role != 'admin':
        return redirect('home')

    pelicula = get_object_or_404(Movie, id=pelicula_id)

    if request.method == 'POST':
        form = MovieForm(request.POST, request.FILES, instance=pelicula)
        if form.is_valid():
            form.save()
            messages.success(request, "Película actualizada correctamente.")
            return redirect('admin_peliculas')
    else:
        form = MovieForm(instance=pelicula)

    return render(request, 'users/admin_pelicula_form.html', {'form': form, 'titulo': f'Editar {pelicula.title}'})


@login_required
def admin_pelicula_eliminar(request, pelicula_id):
    if request.user.role != 'admin':
        return redirect('home')

    pelicula = get_object_or_404(Movie, id=pelicula_id)
    if request.method == 'POST':
        pelicula.delete()
        messages.success(request, "Película eliminada correctamente.")
        return redirect('admin_peliculas')

    return render(request, 'users/admin_pelicula_confirm_delete.html', {'pelicula': pelicula})


# Gestión de funciones
@login_required
def admin_funciones(request):
    if request.user.role != 'admin':
        messages.error(request, "Acceso solo para administradores.")
        return redirect('home')

    funciones = Show.objects.all().select_related('movie', 'room').order_by('-date', '-time')
    return render(request, 'users/admin_funciones.html', {'funciones': funciones})


@login_required
def admin_funcion_crear(request):
    if request.user.role != 'admin':
        return redirect('home')

    if request.method == 'POST':
        form = ShowForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Función creada correctamente.")
            return redirect('admin_funciones')
    else:
        form = ShowForm()

    return render(request, 'users/admin_funcion_form.html', {'form': form, 'titulo': 'Programar Nueva Función'})


@login_required
def admin_funcion_editar(request, funcion_id):
    if request.user.role != 'admin':
        return redirect('home')

    funcion = get_object_or_404(Show, id=funcion_id)

    if request.method == 'POST':
        form = ShowForm(request.POST, instance=funcion)
        if form.is_valid():
            form.save()
            messages.success(request, "Función actualizada correctamente.")
            return redirect('admin_funciones')
    else:
        form = ShowForm(instance=funcion)

    return render(request, 'users/admin_funcion_form.html', {'form': form, 'titulo': f'Editar Función: {funcion.movie.title}'})


@login_required
def admin_funcion_eliminar(request, funcion_id):
    if request.user.role != 'admin':
        return redirect('home')

    funcion = get_object_or_404(Show, id=funcion_id)
    if request.method == 'POST':
        funcion.delete()
        messages.success(request, "Función eliminada correctamente.")
        return redirect('admin_funciones')

    return render(request, 'users/admin_funcion_confirm_delete.html', {'funcion': funcion})


# Gestión de salas (ya lo tienes, lo incluyo completo)
@login_required
def admin_salas(request):
    if request.user.role != 'admin':
        messages.error(request, "Acceso solo para administradores.")
        return redirect('home')

    salas = Room.objects.all().order_by('name')
    return render(request, 'users/admin_salas.html', {'salas': salas})


@login_required
def admin_sala_crear(request):
    if request.user.role != 'admin':
        return redirect('home')

    if request.method == 'POST':
        nombre = request.POST.get('name')
        capacidad = request.POST.get('capacity')

        if nombre and capacidad:
            try:
                capacidad = int(capacidad)
                if capacidad < 1:
                    raise ValueError
                sala = Room.objects.create(name=nombre, capacity=capacidad)
                messages.success(request, f"Sala '{sala.name}' creada correctamente con {capacidad} asientos.")
                return redirect('admin_salas')
            except ValueError:
                messages.error(request, "La capacidad debe ser un número positivo.")
        else:
            messages.error(request, "Completa todos los campos.")
    return render(request, 'users/admin_sala_form.html', {'titulo': 'Crear Nueva Sala'})


@login_required
def admin_sala_editar(request, sala_id):
    if request.user.role != 'admin':
        return redirect('home')

    sala = get_object_or_404(Room, id=sala_id)

    if request.method == 'POST':
        nombre = request.POST.get('name')
        capacidad = request.POST.get('capacity')

        if nombre and capacidad:
            try:
                capacidad = int(capacidad)
                if capacidad < 1:
                    raise ValueError
                sala.name = nombre
                sala.capacity = capacidad
                sala.save()
                messages.success(request, f"Sala actualizada correctamente.")
                return redirect('admin_salas')
            except ValueError:
                messages.error(request, "La capacidad debe ser un número positivo.")
        else:
            messages.error(request, "Completa todos los campos.")
    return render(request, 'users/admin_sala_form.html', {'sala': sala, 'titulo': f'Editar Sala {sala.name}'})


@login_required
def admin_sala_eliminar(request, sala_id):
    if request.user.role != 'admin':
        return redirect('home')

    sala = get_object_or_404(Room, id=sala_id)

    if request.method == 'POST':
        if sala.shows.exists():
            messages.error(request, "No puedes eliminar esta sala porque tiene funciones programadas.")
        else:
            sala.delete()
            messages.success(request, f"Sala '{sala.name}' eliminada correctamente.")
        return redirect('admin_salas')

    return render(request, 'users/admin_sala_confirm_delete.html', {'sala': sala})


# Gestión de usuarios (ya lo tienes, incluido completo)
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash

@login_required
def admin_usuarios(request):
    if request.user.role != 'admin':
        messages.error(request, "Acceso solo para administradores.")
        return redirect('home')

    usuarios = User.objects.all().order_by('username')
    return render(request, 'users/admin_usuarios.html', {'usuarios': usuarios})


@login_required
def admin_usuario_crear(request):
    if request.user.role != 'admin':
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        rol = request.POST.get('role')

        if username and email and password and rol:
            if User.objects.filter(username=username).exists():
                messages.error(request, "Este nombre de usuario ya existe.")
            else:
                try:
                    user = User.objects.create(
                        username=username,
                        email=email,
                        password=make_password(password),
                        role=rol,
                        is_active=True
                    )
                    messages.success(request, f"Usuario '{username}' creado correctamente con rol {rol}.")
                    return redirect('admin_usuarios')
                except Exception as e:
                    messages.error(request, f"Error al crear usuario: {str(e)}")
        else:
            messages.error(request, "Completa todos los campos.")

    roles = User.ROLE_CHOICES
    return render(request, 'users/admin_usuario_form.html', {'titulo': 'Crear Nuevo Usuario', 'roles': roles})


@login_required
def admin_usuario_editar(request, usuario_id):
    if request.user.role != 'admin':
        return redirect('home')

    usuario = get_object_or_404(User, id=usuario_id)

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        rol = request.POST.get('role')
        password = request.POST.get('password')  # opcional
        activo = request.POST.get('is_active') == 'on'

        if username and email and rol:
            if User.objects.exclude(id=usuario.id).filter(username=username).exists():
                messages.error(request, "Este nombre de usuario ya existe.")
            else:
                usuario.username = username
                usuario.email = email
                usuario.role = rol
                usuario.is_active = activo

                if password:
                    usuario.password = make_password(password)
                    if usuario == request.user:
                        update_session_auth_hash(request, usuario)

                usuario.save()
                messages.success(request, f"Usuario '{username}' actualizado correctamente.")
                return redirect('admin_usuarios')
        else:
            messages.error(request, "Completa todos los campos obligatorios.")

    roles = User.ROLE_CHOICES
    return render(request, 'users/admin_usuario_form.html', {
        'usuario': usuario,
        'titulo': f'Editar Usuario {usuario.username}',
        'roles': roles,
    })


@login_required
def admin_usuario_eliminar(request, usuario_id):
    if request.user.role != 'admin':
        return redirect('home')

    usuario = get_object_or_404(User, id=usuario_id)

    if request.method == 'POST':
        if usuario == request.user:
            messages.error(request, "No puedes eliminar tu propia cuenta.")
        else:
            username = usuario.username
            usuario.delete()
            messages.success(request, f"Usuario '{username}' eliminado correctamente.")
        return redirect('admin_usuarios')

    return render(request, 'users/admin_usuario_confirm_delete.html', {'usuario': usuario})


# Reportes
@login_required
def admin_reportes(request):
    if request.user.role != 'admin':
        messages.error(request, "Acceso solo para administradores.")
        return redirect('home')

    today = timezone.now().date()
    start_of_week = today - timezone.timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    ventas_dia = Ticket.objects.filter(purchase_date__date=today, status='paid')
    total_dia = ventas_dia.aggregate(total=Sum('price'))['total'] or 0
    boletos_dia = ventas_dia.count()

    ventas_semana = Ticket.objects.filter(purchase_date__date__gte=start_of_week, status='paid')
    total_semana = ventas_semana.aggregate(total=Sum('price'))['total'] or 0

    ventas_mes = Ticket.objects.filter(purchase_date__date__gte=start_of_month, status='paid')
    total_mes = ventas_mes.aggregate(total=Sum('price'))['total'] or 0

    por_cajero = Ticket.objects.filter(status='paid').values('user__username').annotate(
        total=Sum('price'),
        boletos=Count('id')
    ).order_by('-total')[:5]

    top_peliculas = Ticket.objects.filter(status='paid').values(
        'show_seat__show__movie__title'
    ).annotate(
        boletos=Count('id'),
        ingresos=Sum('price')
    ).order_by('-boletos')[:5]

    context = {
        'total_dia': total_dia,
        'boletos_dia': boletos_dia,
        'total_semana': total_semana,
        'total_mes': total_mes,
        'por_cajero': por_cajero,
        'top_peliculas': top_peliculas,
        'today': today,
    }
    return render(request, 'users/admin_reportes.html', context)


@login_required
def export_reportes_pdf(request):
    if request.user.role != 'admin':
        messages.error(request, "Acceso solo para administradores.")
        return redirect('home')

    today = timezone.now().date()
    start_of_week = today - timezone.timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)

    # Cálculos de reportes
    ventas_dia = Ticket.objects.filter(purchase_date__date=today, status='paid')
    total_dia = ventas_dia.aggregate(total=Sum('price'))['total'] or 0
    boletos_dia = ventas_dia.count()

    ventas_semana = Ticket.objects.filter(purchase_date__date__gte=start_of_week, status='paid')
    total_semana = ventas_semana.aggregate(total=Sum('price'))['total'] or 0

    ventas_mes = Ticket.objects.filter(purchase_date__date__gte=start_of_month, status='paid')
    total_mes = ventas_mes.aggregate(total=Sum('price'))['total'] or 0

    por_cajero = Ticket.objects.filter(status='paid').values('user__username').annotate(
        total=Sum('price'),
        boletos=Count('id')
    ).order_by('-total')[:5]

    top_peliculas = Ticket.objects.filter(status='paid').values(
        'show_seat__show__movie__title'
    ).annotate(
        boletos=Count('id'),
        ingresos=Sum('price')
    ).order_by('-boletos')[:5]

    # Renderizar el template PDF
    html_string = render_to_string('users/admin_reportes_pdf.html', {
        'total_dia': total_dia,
        'boletos_dia': boletos_dia,
        'total_semana': total_semana,
        'total_mes': total_mes,
        'por_cajero': por_cajero,
        'top_peliculas': top_peliculas,
        'today': today,
    })

    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_ventas_sigac.pdf"'
    response.write(pdf)

    return response