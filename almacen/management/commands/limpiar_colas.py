from django.core.management.base import BaseCommand
import django_rq
from rq.registry import StartedJobRegistry


class Command(BaseCommand):
    help = 'Limpia trabajos zombis (Started) de Redis a la fuerza'

    def handle(self, *args, **options):
        queue = django_rq.get_queue('default')
        registry = StartedJobRegistry(queue=queue)
        connection = queue.connection

        count = registry.count
        self.stdout.write(f"Trabajos zombis detectados: {count}")

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No hay nada que limpiar."))
            return

        for job_id in registry.get_job_ids():
            # Eliminar del registro 'Started' a la fuerza
            connection.zrem(registry.key, job_id)

            # Eliminar la data del trabajo
            job = queue.fetch_job(job_id)
            if job:
                job.delete()

            self.stdout.write(f" - Eliminado ID: {job_id}")

        self.stdout.write(self.style.SUCCESS("✅ Limpieza completada exitosamente."))