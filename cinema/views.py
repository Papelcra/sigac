from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from .models import Show, ShowSeat, Ticket, TurnoCaja
from django.template.loader import render_to_string
import os
from weasyprint import HTML
from django.http import HttpResponse
from django.db.models import Sum


def clear_expired_reservations():
    """Libera automáticamente reservas vencidas (estado 'reservado' pasado el tiempo)."""
    now = timezone.now()
    expired = ShowSeat.objects.filter(
        status='reservado',
        reserved_until__lt=now
    )
    count = expired.count()
    if count > 0:
        expired.update(status='disponible', reserved_until=None, reserved_by=None)
        print(f"[AUTO] Liberados {count} asientos vencidos.")  # debug en consola


def movie_list(request):
    """Lista de funciones disponibles (cartelera pública)."""
    clear_expired_reservations()  # Limpiar antes de mostrar disponibilidad

    shows = Show.objects.filter(
        active=True,
        date__gte=timezone.now().date()
    ).select_related('movie', 'room').order_by('date', 'time')
    
    context = {'shows': shows}
    return render(request, 'cinema/movie_list.html', context)


@login_required
def seat_selection(request, show_id):
    """Vista para seleccionar asientos de una función específica."""
    clear_expired_reservations()  # Liberar vencidas antes de mostrar el mapa

    show = get_object_or_404(Show, id=show_id, active=True)

    # Organizar asientos por fila
    seats_by_row = {}
    for show_seat in show.show_seats.select_related('seat').order_by('seat__row', 'seat__number'):
        row = show_seat.seat.row
        seats_by_row.setdefault(row, []).append(show_seat)

    context = {
        'show': show,
        'seats_by_row': sorted(seats_by_row.items()),
        'now': timezone.now(),
    }
    return render(request, 'cinema/seat_selection.html', context)


@login_required
def reserve_seats(request, show_id):
    """Reservar temporalmente asientos seleccionados (10 minutos)."""
    if request.method != 'POST':
        return redirect('seat_selection', show_id=show_id)

    show = get_object_or_404(Show, id=show_id, active=True)
    selected_seat_ids = request.POST.getlist('selected_seats')

    if not selected_seat_ids:
        messages.warning(request, "No seleccionaste ningún asiento.")
        return redirect('seat_selection', show_id=show_id)

    reserved_count = 0
    for seat_id in selected_seat_ids:
        try:
            show_seat = ShowSeat.objects.get(id=seat_id, show=show, status='disponible')
            show_seat.status = 'reservado'
            show_seat.reserved_until = timezone.now() + timedelta(minutes=10)
            show_seat.reserved_by = request.user
            show_seat.save()
            reserved_count += 1
        except ShowSeat.DoesNotExist:
            continue  # Ignorar si ya no está disponible

    if reserved_count > 0:
        messages.success(request, f"¡{reserved_count} asiento(s) reservados por 10 minutos! Dirígete a taquilla.")
    else:
        messages.error(request, "No se pudo reservar (los asientos ya fueron tomados).")

    return redirect('seat_selection', show_id=show_id)


@login_required
def confirm_purchase(request, show_id):
    """Confirmación de compra (para ventas directas o simuladas)."""
    if request.method != 'POST':
        return redirect('seat_selection', show_id=show_id)

    show = get_object_or_404(Show, id=show_id)
    selected_seat_ids = request.POST.getlist('selected_seats')

    if not selected_seat_ids:
        messages.error(request, "No hay asientos seleccionados.")
        return redirect('seat_selection', show_id=show_id)

    tickets_created = []
    for seat_id in selected_seat_ids:
        try:
            show_seat = ShowSeat.objects.get(id=seat_id, show=show, status='reservado', reserved_by=request.user)
            show_seat.status = 'vendido'
            show_seat.reserved_until = None
            show_seat.save()

            ticket = Ticket.objects.create(
                show_seat=show_seat,
                user=request.user,
                price=show.base_price,
                status='paid'
            )
            tickets_created.append(ticket)
        except ShowSeat.DoesNotExist:
            continue

    if tickets_created:
        messages.success(request, f"¡Compra confirmada! Generados {len(tickets_created)} ticket(s).")
        return redirect('ticket_detail', ticket_id=tickets_created[0].id)
    
    messages.error(request, "No se pudo confirmar la compra (asientos ya no disponibles).")
    return redirect('seat_selection', show_id=show_id)


@login_required
def pending_reservations(request):
    """Lista de reservas pendientes para cajeros/admin."""
    if request.user.role not in ['cajero', 'admin']:
        messages.error(request, "No tienes permiso para ver reservas pendientes.")
        return redirect('cajero_dashboard')

    clear_expired_reservations()  # Actualizar lista antes de mostrar

    reservations = ShowSeat.objects.filter(
        status='reservado',
        reserved_by__isnull=False
    ).select_related('show', 'seat', 'reserved_by').order_by('-reserved_until')

    context = {'reservations': reservations}
    return render(request, 'cinema/pending_reservations.html', context)


@login_required
def confirm_sale(request, show_seat_id):
    """Confirmar pago en taquilla por cajero/admin."""
    if request.user.role not in ['cajero', 'admin']:
        messages.error(request, "No tienes permiso para confirmar ventas.")
        return redirect('home')

    show_seat = get_object_or_404(ShowSeat, id=show_seat_id, status='reservado')

    original_user = show_seat.reserved_by
    if not original_user:
        messages.warning(request, "No se encontró usuario original. Usando cajero como fallback.")
        original_user = request.user

    # Marcar asiento como vendido
    show_seat.status = 'vendido'
    show_seat.reserved_until = None
    show_seat.reserved_by = None
    show_seat.save()

    # Crear ticket
    ticket = Ticket.objects.create(
        show_seat=show_seat,
        user=original_user,
        price=show_seat.show.base_price,
        status='paid'
    )

    messages.success(request, f"Pago confirmado. Ticket generado para {show_seat.seat} (ID: {ticket.uuid}).")
    return redirect('pending_reservations')


@login_required
def ticket_detail(request, ticket_id):
    """Detalle del ticket para el cliente."""
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)

    # Generar QR si no existe
    if not ticket.qr_code:
        ticket.generate_qr()

    context = {'ticket': ticket}
    return render(request, 'cinema/ticket_detail.html', context)


@login_required
def download_ticket_pdf(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    
    # Generar QR si no existe
    if not ticket.qr_code:
        ticket.generate_qr()

    # Renderizar el HTML del ticket (reutilizamos o creamos uno específico para PDF)
    html_string = render_to_string('cinema/ticket_pdf.html', {'ticket': ticket})

    # Crear PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf_file = html.write_pdf()

    # Respuesta como descarga
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.uuid}.pdf"'
    response.write(pdf_file)

    return response


@login_required
def validate_ticket(request):
    if request.user.role != 'vigilante':
        messages.error(request, "Acceso solo para vigilantes.")
        return redirect('home')

    context = {}
    ticket = None

    if request.method == 'POST':
        uuid_input = request.POST.get('uuid').strip()

        if uuid_input:
            try:
                ticket = Ticket.objects.get(uuid=uuid_input)
                
                # Validaciones
                if ticket.status != 'paid':
                    messages.error(request, f"Ticket no pagado (estado: {ticket.status}).")
                elif ticket.status == 'used':
                    messages.warning(request, "Este ticket ya fue usado.")
                elif ticket.show_seat.show.date != timezone.now().date():
                    messages.error(request, "La función no es para hoy.")
                else:
                    # Validar OK → marcar como usado
                    ticket.status = 'used'
                    ticket.save()
                    messages.success(request, f"Entrada válida para {ticket.movie_title} - Asiento {ticket.seat_info}.")
                    context['success_ticket'] = ticket
            except Ticket.DoesNotExist:
                messages.error(request, "Ticket no encontrado. Verifica el código.")
        else:
            messages.warning(request, "Ingresa un código de ticket.")

    context['ticket'] = ticket
    return render(request, 'cinema/validate_ticket.html', context)

@login_required
def cierre_caja(request):
    if request.user.role != 'cajero':
        messages.error(request, "Acceso solo para cajeros.")
        return redirect('home')

    # Ventas del día actual (puedes ajustar a turno)
    today = timezone.now().date()
    boletos_hoy = Ticket.objects.filter(
        purchase_date__date=today,
        status='paid'
    ).select_related('show_seat__show')

    total_ingresos = boletos_hoy.aggregate(total=Sum('price'))['total'] or 0
    num_boletos = boletos_hoy.count()

    # Último turno abierto del cajero (si existe)
    turno_abierto = TurnoCaja.objects.filter(
        cajero=request.user,
        cerrado=False
    ).order_by('-fecha_inicio').first()

    if request.method == 'POST':
        if 'cerrar' in request.POST:
            if turno_abierto:
                turno_abierto.fecha_fin = timezone.now()
                turno_abierto.total_ventas = total_ingresos
                turno_abierto.boletos_vendidos = num_boletos
                turno_abierto.notas = request.POST.get('notas', '')
                turno_abierto.cerrado = True
                turno_abierto.save()
                messages.success(request, f"Turno cerrado correctamente. Total: ${total_ingresos:,.2f}")
            else:
                # Crear nuevo turno si no había
                TurnoCaja.objects.create(
                    cajero=request.user,
                    total_ventas=total_ingresos,
                    boletos_vendidos=num_boletos,
                    notas=request.POST.get('notas', ''),
                    cerrado=True
                )
                messages.success(request, "Cierre de caja realizado (sin turno previo abierto).")
            return redirect('cajero_dashboard')

    context = {
        'total_ingresos': total_ingresos,
        'num_boletos': num_boletos,
        'turno_abierto': turno_abierto,
        'boletos_hoy': boletos_hoy,
    }
    return render(request, 'cinema/cierre_caja.html', context)