# semilla360/routing.py
from channels.routing import URLRouter
from django.urls import path, re_path

# Importa los routers de tus apps
import usuarios.routing

# Este es el router principal que asgi.py usará
application = URLRouter([
    path('ws/', URLRouter(
        usuarios.routing.websocket_urlpatterns
    )),
])