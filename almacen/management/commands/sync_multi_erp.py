# almacen/management/commands/sync_multi_erp.py
import logging
import sys
from django.core.management.base import BaseCommand
from django.db import transaction

# Importamos la tarea
from almacen.tasks import sincronizar_empresa_erp_task

# Importamos modelos para el borrado
from almacen.models import (
    MovimientoAlmacen, Transferencia, Stock,
    ControlSyncMovAlmacen, MovimientoAlmacenNota
)
from importaciones.models import Empresa


class Command(BaseCommand):
    help = 'Ejecuta la sincronización ERP (Fase 1) en primer plano.'

    def add_arguments(self, parser):
        parser.add_argument('empresa_alias', type=str, help='Alias de la BD ERP (ej: F001).')
        parser.add_argument('--start-year', type=int, default=2000,
                            help='Año inicial (solo efectivo si es primera vez o con reset).')

        # --- NUEVO ARGUMENTO ---
        parser.add_argument(
            '--days',
            type=int,
            default=5,
            help='Días hacia atrás para la reconciliación (Updates/Deletes). Default: 5. Se ejecuta SIEMPRE.'
        )

        parser.add_argument(
            '--reset-all-data',
            action='store_true',
            help='⚠️ PELIGRO: Borra TODO el historial antes de sincronizar.'
        )

    def handle(self, *args, **options):
        empresa_alias = options['empresa_alias']
        start_year = options['start_year']
        reset_data = options['reset_all_data']

        # Capturamos los días (Default 7 si no se pone nada)
        reconciliation_days = options['days']

        # Configuración de Logs
        task_logger = logging.getLogger('almacen.tasks')
        task_logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        task_logger.addHandler(console_handler)

        try:
            empresa = Empresa.objects.get(nombre_empresa=empresa_alias)
        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Empresa '{empresa_alias}' no encontrada."))
            return

        self.stdout.write(self.style.SUCCESS(f"=== INICIANDO FASE 1 (EXTRACCIÓN) PARA {empresa_alias} ==="))

        # Lógica de Borrado
        if reset_data:
            self.stdout.write(
                self.style.WARNING(f"!!! ALERTA: SE BORRARÁ TODA LA DATA HISTÓRICA DE {empresa_alias} !!!"))
            confirm = input(f"¿Estás 100% seguro? Escribe 'SI' para confirmar: ")

            if confirm == 'SI':
                self.stdout.write("Borrando datos... esto puede tardar unos segundos...")
                with transaction.atomic():
                    ControlSyncMovAlmacen.objects.filter(empresa=empresa).delete()
                    # Borramos tablas de la Fase 1 (Legacy)
                    from almacen.models import LegacyMovAlmCab, LegacyMovAlmDet
                    LegacyMovAlmDet.objects.filter(empresa=empresa).delete()
                    LegacyMovAlmCab.objects.filter(empresa=empresa).delete()

                    # También limpiamos las tablas finales para empezar limpio
                    Transferencia.objects.filter(empresa=empresa).delete()
                    MovimientoAlmacen.objects.filter(empresa=empresa).delete()
                    Stock.objects.filter(empresa=empresa).delete()

                    self.stdout.write(self.style.SUCCESS("✅ LIMPIEZA COMPLETA (Legacy + Finales)."))
            else:
                self.stdout.write(self.style.ERROR("Operación cancelada. Saliendo."))
                return

        # Ejecución Síncrona
        self.stdout.write(
            self.style.SUCCESS(f"⏳ Iniciando sincronización... (Reconciliación: últimos {reconciliation_days} días)"))

        try:
            # Llamamos a la función pasando el nuevo argumento
            resultado = sincronizar_empresa_erp_task(
                empresa_alias=empresa_alias,
                start_year=start_year,
                reconciliation_days=reconciliation_days,  # <-- Pasamos el valor aquí
                user_id=None
            )

            self.stdout.write(self.style.SUCCESS(f"\n✨ PROCESO FINALIZADO: {resultado}"))

        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("\n⛔ Proceso interrumpido por el usuario (Ctrl+C)."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Ocurrió un error durante la ejecución: {str(e)}"))
        finally:
            task_logger.removeHandler(console_handler)