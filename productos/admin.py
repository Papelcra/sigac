from django.contrib import admin
from .models import Producto, Combo
from .models import Producto, Combo, VentaProducto
admin.site.register(Producto)
admin.site.register(Combo)



admin.site.register(VentaProducto)