from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

# Importamos el modelo Ticket (asegúrate de que esté en cinema/models.py)
from cinema.models import Ticket


def home(request):
    """Vista raíz: redirige según rol si está autenticado, sino al login"""
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
        else:
            messages.warning(request, "Rol no reconocido. Contacta al administrador.")
            return redirect('login')
    return redirect('login')


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
        dashboard = role_redirects.get(self.request.user.role)
        if dashboard:
            return reverse_lazy(dashboard)
        return reverse_lazy('login')  # fallback


@login_required
def admin_dashboard(request):
    return render(request, 'users/admin_dashboard.html')


@login_required
def cajero_dashboard(request):
    return render(request, 'users/cajero_dashboard.html')


@login_required
def vendedor_dashboard(request):
    return render(request, 'users/vendedor_dashboard.html')


@login_required
def vigilante_dashboard(request):
    return render(request, 'users/vigilante_dashboard.html')


@login_required
def cliente_dashboard(request):
    if request.user.role != 'cliente':
        messages.error(request, "Acceso no autorizado.")
        return redirect('home')

    tickets = Ticket.objects.filter(
        user=request.user,
        # status__in=['paid', 'used']  # ← original
        # Para pruebas: quita el filtro de status temporalmente
    ).select_related(
        'show_seat__show__movie',
        'show_seat__seat'
    ).order_by('-purchase_date')

    context = {
        'tickets': tickets,
    }
    return render(request, 'users/cliente_dashboard.html', context)