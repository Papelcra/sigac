from django.contrib import admin
from .models import Movie, Room, Seat, Show, Ticket

admin.site.register(Movie)
admin.site.register(Room)
admin.site.register(Seat)
admin.site.register(Show)
admin.site.register(Ticket)