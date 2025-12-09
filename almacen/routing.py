'''
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ruta específica de esta app
    re_path(r'sync-status/$', consumers.SyncStatusConsumer.as_asgi()),
]
'''