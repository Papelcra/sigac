from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from .models import Show, ShowSeat, Ticket, TurnoCaja
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.db.models import Sum
# Librería para generar PDF (estable en Render y local)
from xhtml2pdf import pisa

# Para confitería y precios precisos (de la rama de tu compañera)
from decimal import Decimal
from .models import Producto, Combo, VentaConfiteria, DetalleVentaConfiteria


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

    # Renderizar el HTML del ticket
    html_string = render_to_string('cinema/ticket_pdf.html', {'ticket': ticket})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.uuid}.pdf"'

    # Generar PDF con xhtml2pdf
    pisa_status = pisa.CreatePDF(
        src=html_string,
        dest=response,
        encoding='utf-8'
    )

    if pisa_status.err:
        messages.error(request, "Error al generar el PDF del ticket. Revisa el contenido.")
        return redirect('ticket_detail', ticket_id=ticket.id)

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

    today = timezone.now().date()
    boletos_hoy = Ticket.objects.filter(
        purchase_date__date=today,
        status='paid'
    ).select_related('show_seat__show')

    total_ingresos = boletos_hoy.aggregate(total=Sum('price'))['total'] or 0
    num_boletos = boletos_hoy.count()

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


@login_required
def vendedor_dashboard(request):
    # Asegúrate de usar el modelo correcto
    lista_productos = Producto.objects.all() 
    lista_combos = Combo.objects.all()
    return render(request, "users/vendedor_dashboard.html",{
    'productos': lista_productos,
    'combos': lista_combos,
})

@login_required
def vender_producto(request, id):

    producto = get_object_or_404(Producto, id=id)

    if request.method == "POST":

        if producto.stock <= 0:
            messages.error(request, "No hay stock disponible")
            return redirect("vendedor_dashboard")

        producto.stock -= 1
        producto.save()

        messages.success(request, f"Se vendió {producto.nombre}")

    return redirect("vendedor_dashboard")

@login_required
def vender_combo(request, id):

    combo = get_object_or_404(Combo, id=id)

    if request.method == "POST":

        for producto in combo.productos.all():

            if producto.stock <= 0:
                messages.error(request, f"No hay stock de {producto.nombre}")
                return redirect("vendedor_dashboard")

        for producto in combo.productos.all():
            producto.stock -= 1
            producto.save()

        messages.success(request, f"Se vendió el combo {combo.nombre}")

    return redirect("vendedor_dashboard")

from .models import CompraCombo

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

    combos = Combo.objects.all()

    # CONSULTAR COMBOS COMPRADOS
    combos_comprados = CompraCombo.objects.filter(
        usuario=request.user
    ).select_related('combo').order_by('-fecha')

    context = {
        'tickets': tickets,
        'combos': combos,
        'combos_comprados': combos_comprados
    }

    return render(request, 'users/cliente_dashboard.html', context)


def admin_productos(request):

    productos = Producto.objects.all()

    return render(request, 'users/admin_productos.html', {
        'productos': productos
    })


def admin_combos(request):
    combos = Combo.objects.all()

    return render(request, 'users/admin_combos.html', {
        'combos': combos
    })

@login_required
def crear_producto(request):

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        precio = request.POST.get("precio")
        stock = request.POST.get("stock")

        Producto.objects.create(
            nombre=nombre,
            precio=precio,
            stock=stock
        )

        messages.success(request, "Producto creado correctamente.")
        return redirect("admin_productos")

    return render(request, "users/crear_producto.html")

@login_required
def editar_producto(request, id):    

    producto = get_object_or_404(Producto, id=id)

    if request.method == "POST":
        producto.nombre = request.POST.get("nombre")
        producto.precio = request.POST.get("precio")
        producto.stock = request.POST.get("stock")
        producto.save()

        messages.success(request, "Producto actualizado correctamente.")
        return redirect("admin_productos")

    return render(request, "users/editar_producto.html", {
        "producto": producto
    })

@login_required
def eliminar_producto(request, id):   

    producto = get_object_or_404(Producto, id=id)

    if request.method == "POST":
        producto.delete()
        messages.success(request, "Producto eliminado correctamente.")
        return redirect("admin_productos")

    return render(request, "users/eliminar_producto.html", {
        "producto": producto
    })  

@login_required
def crear_combo(request):

    productos = Producto.objects.all()

    if request.method == "POST":

        nombre = request.POST.get("nombre")
        productos_ids = request.POST.getlist("productos")

        productos_seleccionados = Producto.objects.filter(id__in=productos_ids)

        total = sum(p.precio for p in productos_seleccionados)

        descuento = Decimal("0.10")  # 10%
        precio_combo = total * (Decimal("1.00") - descuento)

        combo = Combo.objects.create(
            nombre=nombre,
            precio=precio_combo
        )

        combo.productos.set(productos_seleccionados)

        messages.success(request, "Combo creado correctamente")
        return redirect("admin_combos")

    return render(request, "users/crear_combo.html", {
        "productos": productos
    })
@login_required
def editar_combo(request, id):

    combo = get_object_or_404(Combo, id=id)
    productos = Producto.objects.all()

    if request.method == "POST":

        combo.nombre = request.POST.get("nombre")
        productos_ids = request.POST.getlist("productos")

        productos_seleccionados = Producto.objects.filter(id__in=productos_ids)

        total = sum(p.precio for p in productos_seleccionados)

        descuento = Decimal("0.10")
        precio_combo = total * (Decimal("1.00") - descuento)

        combo.precio = precio_combo.quantize(Decimal("0.01"))

        combo.save()
        combo.productos.set(productos_seleccionados)

        messages.success(request, "Combo actualizado correctamente.")
        return redirect("admin_combos")

    return render(request, "users/editar_combo.html", {
        "combo": combo,
        "productos": productos
    })

@login_required
def eliminar_combo(request, id):

    combo = get_object_or_404(Combo, id=id)

    if request.method == "POST":
        combo.delete()
        messages.success(request, "Combo eliminado.")
        return redirect("admin_combos")

    return render(request, "users/eliminar_combo.html", {
        "combo": combo
    })

from django.contrib import messages

