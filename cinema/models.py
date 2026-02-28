from django.db import models
from django.utils import timezone
import string
from django.core.exceptions import ValidationError
import uuid
import qrcode
from io import BytesIO
from django.core.files import File


class Movie(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration = models.PositiveIntegerField(help_text="Duración en minutos")
    release_date = models.DateField()
    active = models.BooleanField(default=True)
    poster = models.ImageField(upload_to='posters/', null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Película"
        verbose_name_plural = "Películas"


class Room(models.Model):
    name = models.CharField(max_length=50, unique=True)
    capacity = models.PositiveIntegerField(help_text="Capacidad total de la sala")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            seats_per_row = 10
            rows_needed = (self.capacity + seats_per_row - 1) // seats_per_row
            rows = string.ascii_uppercase[:rows_needed]

            total_created = 0
            for row in rows:
                for number in range(1, seats_per_row + 1):
                    if total_created >= self.capacity:
                        break
                    Seat.objects.create(room=self, row=row, number=number)
                    total_created += 1

            if total_created != self.capacity:
                raise ValidationError(f"Error al generar asientos: {total_created} creados de {self.capacity} esperados")


class Seat(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="seats")
    row = models.CharField(max_length=5)
    number = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.room.name} - {self.row}{self.number}"

    class Meta:
        unique_together = ('room', 'row', 'number')
        ordering = ['row', 'number']
        verbose_name = "Asiento"
        verbose_name_plural = "Asientos"


class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="shows")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="shows")
    date = models.DateField()
    time = models.TimeField()
    active = models.BooleanField(default=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.movie.title} - {self.date} {self.time.strftime('%H:%M')} ({self.room.name})"

    def clean(self):
        naive_dt = timezone.datetime.combine(self.date, self.time)
        show_datetime = timezone.make_aware(naive_dt)
        
        if show_datetime < timezone.now():
            raise ValidationError("La función no puede ser en el pasado.")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Siempre verificar y crear ShowSeat si faltan
        existing_seats = self.show_seats.count()
        total_seats = self.room.seats.count()
        
        if existing_seats < total_seats:
            for seat in self.room.seats.all():
                if not self.show_seats.filter(seat=seat).exists():
                    ShowSeat.objects.create(
                        show=self,
                        seat=seat,
                        status='disponible'
                    )

    class Meta:
        verbose_name = "Función"
        verbose_name_plural = "Funciones"
        ordering = ['date', 'time']


class ShowSeat(models.Model):
    STATUS_CHOICES = (
        ('disponible', 'Disponible'),
        ('reservado', 'Reservado (temporal)'),
        ('vendido', 'Vendido'),
    )

    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='show_seats')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='show_seats')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='disponible')
    reserved_until = models.DateTimeField(null=True, blank=True)
    reserved_by = models.ForeignKey('users.User', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('show', 'seat')
        verbose_name = "Asiento en Función"
        verbose_name_plural = "Asientos en Función"

    def __str__(self):
        return f"{self.seat} en {self.show} → {self.status}"

    def is_available(self):
        if self.status == 'disponible':
            return True
        if self.status == 'reservado' and self.reserved_until and self.reserved_until < timezone.now():
            self.status = 'disponible'
            self.reserved_until = None
            self.reserved_by = None
            self.save(update_fields=['status', 'reserved_until', 'reserved_by'])
            return True
        return False


class Ticket(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    show_seat = models.ForeignKey(ShowSeat, on_delete=models.CASCADE, related_name='tickets')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True)
    purchase_date = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=(('pending', 'Pendiente'), ('paid', 'Pagado'), ('used', 'Usado'), ('cancelled', 'Cancelado')),
        default='pending'
    )
    qr_code = models.ImageField(upload_to='tickets_qr/', null=True, blank=True)

    def __str__(self):
        return f"Ticket {self.uuid} - {self.show_seat}"

    @property
    def movie_title(self):
        return self.show_seat.show.movie.title

    @property
    def seat_info(self):
        return f"{self.show_seat.seat.room.name} - {self.show_seat.seat}"

    def generate_qr(self):
        if self.qr_code:
            return  # ya existe

        try:
            qr_content = str(self.uuid)  # o "SIGAC Ticket: {self.uuid}"

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            file_name = f"ticket_{self.uuid}.png"
            self.qr_code.save(file_name, File(buffer), save=False)
            self.save(update_fields=['qr_code'])
        except Exception as e:
            print(f"Error generando QR para ticket {self.uuid}: {e}")  # debug en consola

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.qr_code:  # genera solo si no existe
            self.generate_qr()

    class Meta:
        ordering = ['-purchase_date']