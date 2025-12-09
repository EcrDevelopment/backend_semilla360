# semilla360/asgi.py (CORREGIDO Y ORDENADO)

import os
from django.core.asgi import get_asgi_application

# --- PASO 1: Configurar Django PRIMERO ---
# Establece la variable de entorno ANTES de importar nada de Django.
# (¡Asegúrate de que el typo 'semilla306' esté corregido aquí!)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'semilla360.settings')

# Llama a get_asgi_application() aquí. Esto inicializa Django (django.setup())
# y prepara la aplicación HTTP que Daphne también servirá.
django_asgi_app = get_asgi_application()

# --- PASO 2: Importar Channels y tu código DESPUÉS ---
# Ahora que Django está configurado, podemos importar de forma segura
# tu middleware y routing, que dependen de los modelos de Django.
from channels.routing import ProtocolTypeRouter, URLRouter
from usuarios.middleware import JwtAuthMiddleware
import semilla360.routing # El router raíz que creamos

# --- PASO 3: Definir la Aplicación ---
application = ProtocolTypeRouter({

    # La aplicación HTTP de Django maneja las vistas HTTP normales
    "http": django_asgi_app,

    # La aplicación WebSocket maneja las conexiones WS
    "websocket": JwtAuthMiddleware(
        semilla360.routing.application
    ),
})# semilla360/asgi.py (CORREGIDO Y ORDENADO)

import os
from django.core.asgi import get_asgi_application

# --- PASO 1: Configurar Django PRIMERO ---
# Establece la variable de entorno ANTES de importar nada de Django.
# (¡Asegúrate de que el typo 'semilla306' esté corregido aquí!)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'semilla360.settings')

# Llama a get_asgi_application() aquí. Esto inicializa Django (django.setup())
# y prepara la aplicación HTTP que Daphne también servirá.
django_asgi_app = get_asgi_application()

# --- PASO 2: Importar Channels y tu código DESPUÉS ---
# Ahora que Django está configurado, podemos importar de forma segura
# tu middleware y routing, que dependen de los modelos de Django.
from channels.routing import ProtocolTypeRouter, URLRouter
from usuarios.middleware import JwtAuthMiddleware
import semilla360.routing # El router raíz que creamos

# --- PASO 3: Definir la Aplicación ---
application = ProtocolTypeRouter({

    # La aplicación HTTP de Django maneja las vistas HTTP normales
    "http": django_asgi_app,

    # La aplicación WebSocket maneja las conexiones WS
    "websocket": JwtAuthMiddleware(
        semilla360.routing.application
    ),
})