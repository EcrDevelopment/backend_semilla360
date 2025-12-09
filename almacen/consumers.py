import json


# Ya no heredamos de AsyncWebsocketConsumer, es una clase "Mixin" pura para lógica
class SyncStatusMixin:
    """
    Mixin que contiene EXCLUSIVAMENTE la lógica de cómo procesar
    los mensajes que vienen de la tarea de sincronización.
    """

    async def sync_update(self, event):
        """
        Este método será heredado por el Consumer Principal.
        Aquí defines CÓMO se formatea y envía el mensaje de esta tarea específica.
        """
        # Validamos que el evento traiga datos
        if not event:
            return

        # Construimos el payload para el frontend
        response_data = {
            'type': 'sync_update',  # El frontend escucha esto
            'status': event.get('status'),
            'message': event.get('message'),
            'result': event.get('result'),
        }

        #print(f"[Almacen Mixin] Enviando update: {response_data['message']}")

        # 'self.send' funcionará porque quien use este Mixin será un WebsocketConsumer
        await self.send(text_data=json.dumps(response_data))