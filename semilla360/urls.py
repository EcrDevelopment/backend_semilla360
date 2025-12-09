#semilla360/urls.py
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('api/admin/', admin.site.urls),
    path('api/accounts/', include('usuarios.urls')),
    path('api/importaciones/', include('importaciones.urls')),
    path('api/localizacion/',include('localizacion.urls')),
    path('api/almacen/',include('almacen.urls')),

]

