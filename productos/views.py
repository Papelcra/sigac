from django.shortcuts import render, redirect
from .models import Producto, VentaProducto


def lista_productos(request):
    productos = Producto.objects.filter(activo=True)

    return render(request, "productos/lista.html", {
        "productos": productos
    })


def vender_producto(request):

    productos = Producto.objects.filter(activo=True)

    if request.method == "POST":

        producto_id = request.POST.get("producto")
        cantidad = request.POST.get("cantidad")

        if not producto_id or not cantidad:
            return render(request, "productos/vender.html", {
                "productos": productos,
                "error": "Debe seleccionar producto y cantidad"
            })

        try:
            producto = Producto.objects.get(id=producto_id)
        except Producto.DoesNotExist:
            return render(request, "productos/vender.html", {
                "productos": productos,
                "error": "El producto no existe"
            })

        cantidad = int(cantidad)

        if producto.stock < cantidad:
            return render(request, "productos/vender.html", {
                "productos": productos,
                "error": "No hay suficiente stock"
            })

        total = producto.precio * cantidad

        VentaProducto.objects.create(
            producto=producto,
            cantidad=cantidad,
            total=total
        )

        producto.stock -= cantidad
        producto.save()

        return render(request, "productos/vender.html", {
            "productos": productos,
            "mensaje": "Venta realizada correctamente 🎉"
        })

    return render(request, "productos/vender.html", {
        "productos": productos
    })