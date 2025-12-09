# usuarios/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

from almacen.consumers import SyncStatusMixin


# ¡El nombre de este grupo ahora es GENÉRICO!
# Este es el grupo "personal" del usuario, para notificaciones generales.
def get_user_group_name(user_id):
    return f"user_{user_id}"


class MainConsumer(SyncStatusMixin,AsyncWebsocketConsumer):
    """
    Este es ahora el ÚNICO consumer que maneja al usuario.
    Autentica y luego espera mensajes de "subscribe" y "unsubscribe".
    """

    async def connect(self):
        self.user = self.scope["user"]
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # 1. Unirse al grupo "personal"
        # (Ideal para notificaciones de "Tu perfil fue actualizado", etc.)
        self.user_group_name = get_user_group_name(self.user.id)
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # 2. Creamos un set para guardar las suscripciones "extra"
        self.subscribed_groups = set()

        await self.accept()

    async def disconnect(self, close_code):
        # 1. Salir del grupo "personal"
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

        # 2. Salir de TODOS los otros grupos a los que se suscribió
        for group in self.subscribed_groups:
            await self.channel_layer.group_discard(
                group,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Se llama cuando el FRONTEND (React) envía un mensaje.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            stream_name = data.get('stream')  # ej: 'sync_empresa_5'

            if not message_type or not stream_name:
                return

            # El group_name en este caso será la empresa
            group_name = stream_name

            if message_type == 'subscribe':
                #print(f"[Consumer] Suscribiendo a GRUPO PÚBLICO: {group_name}")
                await self.channel_layer.group_add(group_name, self.channel_name)
                # (Ya no necesitas self.subscribed_groups si solo es un grupo a la vez)

            elif message_type == 'unsubscribe':
                #print(f"[Consumer] Desuscribiendo de GRUPO PÚBLICO: {group_name}")
                await self.channel_layer.group_discard(group_name, self.channel_name)

        except json.JSONDecodeError:
            print("[Consumer] Error: Mensaje no es JSON válido")

    # --- Tu handler de mensajes (PERFECTO) ---
    '''
    async def sync_update(self, event):
        """
        Manejador para el evento 'sync.update'.
        Esto lo llama tu tarea de RQ.
        """
        #print(f"DEBUG WS: 'sync_update' recibido del channel layer: {event}")
        await self.send(text_data=json.dumps({
            'type': 'sync_update',  # El frontend filtra por este 'type'
            'status': event.get('status'),
            'message': event.get('message'),
            'result': event.get('result'),
        }))
    '''

    # (Puedes añadir más handlers genéricos aquí...)
    async def general_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'general_notification',
            'message': event.get('message'),
        }))