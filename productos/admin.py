from django.contrib import admin
from .models import Producto, Combo
from .models import Producto, Combo, VentaProductoLocal
admin.site.register(Producto)
admin.site.register(Combo)



admin.site.register(VentaProductoLocal)