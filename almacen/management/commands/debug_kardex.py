from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from almacen.models import MovimientoAlmacen, Producto, Empresa, Almacen
import datetime


class Command(BaseCommand):
    help = 'Diagnóstico profundo de fechas y stock'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=== INICIO DE DIAGNÓSTICO DE KÁRDEX ==="))

        # 1. Verificación de Configuración
        self.stdout.write("\n1. CONFIGURACIÓN DE ZONA HORARIA:")
        self.stdout.write(f"   TIME_ZONE (settings): {getattr(settings, 'TIME_ZONE', 'No definido')}")
        self.stdout.write(f"   USE_TZ (settings): {getattr(settings, 'USE_TZ', 'No definido')}")
        self.stdout.write(f"   Hora actual del servidor (Python): {datetime.datetime.now()}")
        self.stdout.write(f"   Hora actual (Django Aware): {timezone.now()}")

        # 2. Buscar el producto problemático
        cod_producto = 'HIS00001'  # El de tu captura
        alias_empresa = 'bd_trading_starsoft'  # El de tu captura
        cod_almacen = 'AL'  # Almacen Lima

        try:
            empresa = Empresa.objects.get(nombre_empresa=alias_empresa)
            producto = Producto.objects.get(empresa=empresa, codigo_producto=cod_producto)
            almacen = Almacen.objects.get(empresa=empresa, codigo=cod_almacen)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error buscando datos maestros: {e}"))
            return

        self.stdout.write(f"\n2. DATOS ENCONTRADOS:")
        self.stdout.write(f"   Empresa ID: {empresa.id}, Almacen ID: {almacen.id}, Producto ID: {producto.id}")

        # 3. Verificación de Datos CRUDOS en BD
        self.stdout.write("\n3. MUESTRA DE DATOS CRUDOS (Primeros 5 movimientos):")
        # Traemos todo sin filtros de fecha para ver qué hay realmente
        qs_raw = MovimientoAlmacen.objects.filter(
            empresa=empresa, almacen=almacen, producto=producto
        ).order_by('fecha_documento')[:5]

        if not qs_raw.exists():
            self.stdout.write(self.style.ERROR("   ¡LA TABLA ESTÁ VACÍA PARA ESTE PRODUCTO!"))
            self.stdout.write("   Posible causa: El comando process_legacy_data falló o borró todo sin rellenar.")
        else:
            for mov in qs_raw:
                self.stdout.write(
                    f"   ID: {mov.id} | Fecha Doc (Raw): {mov.fecha_documento} | Tipo: {mov.tipo_documento_erp}-{mov.numero_documento_erp} | Cant: {mov.cantidad}")

        # 4. Simulación del Filtro Problemático
        fecha_inicio_str = "2025-09-01"  # El filtro que usabas antes
        fecha_fin_str = "2025-09-30"

        fecha_inicio = datetime.datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        fecha_fin = datetime.datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()

        self.stdout.write(f"\n4. PRUEBA DE FILTRO (Rango: {fecha_inicio} al {fecha_fin}):")

        # A. Prueba con __date (La que falla)
        qs_date = MovimientoAlmacen.objects.filter(
            empresa=empresa, almacen=almacen, producto=producto,
            fecha_documento__date__range=[fecha_inicio, fecha_fin]
        )
        count_date = qs_date.count()
        self.stdout.write(f"   A. Usando filtro '__date__range': Encontrados {count_date} registros.")
        self.stdout.write(f"      SQL Generado: {qs_date.query}")

        # B. Prueba con Datetime Range (Manual)
        start_dt = timezone.make_aware(datetime.datetime.combine(fecha_inicio, datetime.time.min))
        end_dt = timezone.make_aware(datetime.datetime.combine(fecha_fin, datetime.time.max))

        qs_manual = MovimientoAlmacen.objects.filter(
            empresa=empresa, almacen=almacen, producto=producto,
            fecha_documento__range=[start_dt, end_dt]
        )
        count_manual = qs_manual.count()
        self.stdout.write(
            f"   B. Usando filtro datetime manual ({start_dt} a {end_dt}): Encontrados {count_manual} registros.")