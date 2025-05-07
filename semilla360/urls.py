from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('api/admin/', admin.site.urls),
    path('api/importaciones/', include('importaciones.urls')),
    path('api/accounts/', include('usuarios.urls')),
]

