from django.contrib import admin
from .models import Movie, Room, Seat, Show, ShowSeat, Ticket


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'release_date', 'duration', 'active', 'poster_preview')
    list_filter = ('active', 'release_date')
    search_fields = ('title', 'description')
    readonly_fields = ('poster_preview',)

    def poster_preview(self, obj):
        if obj.poster:
            return f'<img src="{obj.poster.url}" width="100" style="border-radius:4px;">'
        return "Sin póster"
    poster_preview.short_description = "Póster"
    poster_preview.allow_tags = True


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity', 'seat_count')
    readonly_fields = ('seat_count',)

    def seat_count(self, obj):
        return obj.seats.count()
    seat_count.short_description = "Asientos generados"


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'room')
    list_filter = ('room',)
    search_fields = ('room__name', 'row', 'number')


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ('movie', 'room', 'date', 'time', 'base_price', 'active')
    list_filter = ('active', 'date', 'room')
    search_fields = ('movie__title', 'room__name')
    date_hierarchy = 'date'
    readonly_fields = ('show_seat_count',)

    def show_seat_count(self, obj):
        return obj.show_seats.count()
    show_seat_count.short_description = "Asientos creados"


@admin.register(ShowSeat)
class ShowSeatAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'reserved_until', 'reserved_by')
    list_filter = ('status', 'show__date', 'show__room')
    search_fields = ('show__movie__title', 'seat__room__name', 'reserved_by__username')
    raw_id_fields = ('show', 'seat', 'reserved_by')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'show_seat', 'user', 'status', 'purchase_date', 'price')
    list_filter = ('status', 'purchase_date')
    search_fields = ('uuid', 'user__username', 'show_seat__show__movie__title')
    date_hierarchy = 'purchase_date'
    readonly_fields = ('uuid', 'purchase_date')