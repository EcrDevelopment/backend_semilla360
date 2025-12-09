from django.core.management.base import BaseCommand
from almacen.models import LegacyMovAlmCab, LegacyMovAlmDet, MovimientoAlmacen, Producto, Almacen, Empresa


class Command(BaseCommand):
    help = 'Encuentra diferencias entre Legacy (ERP) y MovimientoAlmacen (Local)'

    def add_arguments(self, parser):
        parser.add_argument('empresa_alias', type=str)
        parser.add_argument('codigo_producto', type=str)
        parser.add_argument('codigo_almacen', type=str)

    def handle(self, *args, **options):
        empresa_alias = options['empresa_alias']
        cod_prod = options['codigo_producto']
        cod_alm = options['codigo_almacen']

        self.stdout.write(self.style.WARNING(f"--- Buscando diferencias para {cod_prod} en {cod_alm} ---"))

        # 1. Obtener objetos maestros
        try:
            empresa = Empresa.objects.get(nombre_empresa=empresa_alias)
            producto = Producto.objects.get(empresa=empresa, codigo_producto=cod_prod)
            almacen = Almacen.objects.get(empresa=empresa, codigo=cod_alm)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error buscando maestros: {e}"))
            return

        # 2. Cargar CABECERAS Legacy válidas en memoria (Diccionario)
        # Traemos todas las cabeceras de ese almacén que NO sean Anuladas
        print("Cargando Cabeceras Legacy...", end="\r")
        cabs_qs = LegacyMovAlmCab.objects.filter(
            empresa=empresa,
            caalma=cod_alm
        ).exclude(casitgui='A')  # Filtro Base 1: No Anulados

        # Mapa: { ('NI', '000123'): ObjetoCabecera }
        valid_cabs = {}

        for cab in cabs_qs.iterator():
            doc_tipo = cab.catd.strip()
            cod_mov = (cab.cacodmov or '').strip()
            sit_gui = (cab.casitgui or '').strip()

            # --- Filtros del SP (Replicados aquí manualmente) ---
            # Filtro GS-GF-F
            if doc_tipo == 'GS' and cod_mov == 'GF' and sit_gui == 'F':
                continue
            # Filtro NS-AJ
            if doc_tipo == 'NS' and cod_mov == 'AJ':
                continue

            # Clave única: Tipo + Número
            key = (doc_tipo, cab.canumdoc.strip())
            valid_cabs[key] = cab

        self.stdout.write(f"Cabeceras Legacy Válidas cargadas: {len(valid_cabs)}")

        # 3. Cargar DETALLES Legacy y cruzar con Cabeceras
        print("Cargando Detalles Legacy...", end="\r")
        dets_qs = LegacyMovAlmDet.objects.filter(
            empresa=empresa,
            dealma=cod_alm,
            decodigo=cod_prod
        )

        erp_docs = {}  # { 'NI-000123': 500.00 }
        total_erp = 0

        for det in dets_qs.iterator():
            tipo = det.detd.strip()
            num = det.denumdoc.strip()

            # Buscamos si la cabecera existe en nuestro mapa de válidos
            cab = valid_cabs.get((tipo, num))

            if not cab:
                # Si no está en valid_cabs, es porque era Anulada o filtrada (GF, AJ).
                # La ignoramos.
                continue

            key_str = f"{tipo}-{num}"

            cantidad = float(det.decantid or 0)

            # Lógica IN/OUT basada en CATIPMOV (Tal como lo hace el SP y tu tarea ahora)
            if cab.catipmov == 'S':
                cantidad = -cantidad

            erp_docs[key_str] = erp_docs.get(key_str, 0) + cantidad
            total_erp += cantidad

        self.stdout.write(f"ERP Total Calculado: {total_erp:,.2f} (Docs: {len(erp_docs)})")

        # 4. Obtener Data Local (MovimientoAlmacen)
        print("Cargando Data Local...", end="\r")
        local_qs = MovimientoAlmacen.objects.filter(
            empresa=empresa,
            producto=producto,
            almacen=almacen,
            state=True
        )

        local_docs = {}
        total_local = 0

        for mov in local_qs.iterator():
            key_str = f"{mov.tipo_documento_erp}-{mov.numero_documento_erp}"

            cantidad = float(mov.cantidad)
            if not mov.es_ingreso:
                cantidad = -cantidad

            local_docs[key_str] = local_docs.get(key_str, 0) + cantidad
            total_local += cantidad

        self.stdout.write(f"Local Total Calculado: {total_local:,.2f} (Docs: {len(local_docs)})")

        diff_total = total_local - total_erp
        self.stdout.write(self.style.WARNING(f"DIFERENCIA TOTAL (Local - ERP): {diff_total:,.2f}"))

        if abs(diff_total) < 0.01:
            self.stdout.write(self.style.SUCCESS("¡Cuadra perfecto!"))
            return

        # 5. Encontrar las diferencias
        self.stdout.write("\n--- 🕵️ DETECTIVE DE DIFERENCIAS ---")

        all_keys = set(erp_docs.keys()) | set(local_docs.keys())
        count_diffs = 0

        # Ordenamos para ver cronología si es posible (o alfabético)
        for key in sorted(list(all_keys)):
            val_erp = erp_docs.get(key, 0)
            val_local = local_docs.get(key, 0)

            diff = val_local - val_erp

            if abs(diff) > 0.01:
                msg = f"{key} | ERP: {val_erp:,.2f} | Local: {val_local:,.2f} | Diff: {diff:,.2f}"

                if val_local == 0 and val_erp != 0:
                    self.stdout.write(self.style.ERROR(f"[FALTA EN LOCAL] {msg}"))
                elif val_erp == 0 and val_local != 0:
                    self.stdout.write(self.style.WARNING(f"[SOBRA EN LOCAL] {msg}"))
                else:
                    self.stdout.write(f"[MONTO DISTINTO] {msg}")

                count_diffs += 1
                if count_diffs >= 50:  # Límite para no saturar consola
                    self.stdout.write("... (demasiados errores, mostrando primeros 50)")
                    break