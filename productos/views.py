from django.shortcuts import render, redirect
from .models import Producto, VentaProducto
import json



def lista_productos(request):
    productos = Producto.objects.filter(activo=True)

    return render(request, "productos/lista.html", {
        "productos": productos
    })




def vender_producto(request):

    productos = Producto.objects.filter(activo=True)

    if request.method == "POST":

        carrito = json.loads(request.POST.get("carrito"))

        for item in carrito:

            producto = Producto.objects.get(id=item["id"])

            VentaProducto.objects.create(
                producto=producto,
                cantidad=item["cantidad"],
                total=item["subtotal"]
            )

            producto.stock -= item["cantidad"]
            producto.save()

        return render(request,"productos/vender.html",{
            "productos":productos,
            "mensaje":"Venta registrada correctamente"
        })

    return render(request,"productos/vender.html",{
        "productos":productos
    })