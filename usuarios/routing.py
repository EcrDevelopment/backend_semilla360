# usuarios/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Ruta genérica (el nombre 'sync-status' ya no va aquí)
    re_path(r'notifications/$', consumers.MainConsumer.as_asgi()),
    #re_path(r'ws/almacen/sync/$', alm_consumers.SyncStatusConsumer.as_asgi()),
]