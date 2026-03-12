from django.urls import path
from .views import vender_producto

urlpatterns = [
    path('vender/', vender_producto, name='vender_producto'),
]