# Documentación Detallada del Módulo Almacén

## Índice
1. [Introducción y Propósito](#introducción-y-propósito)
2. [Arquitectura del Módulo](#arquitectura-del-módulo)
3. [Modelos de Datos](#modelos-de-datos)
4. [Sistema de Sincronización](#sistema-de-sincronización)
5. [API Endpoints](#api-endpoints)
6. [Funcionalidades Principales](#funcionalidades-principales)
7. [Servicios y Utilidades](#servicios-y-utilidades)
8. [Sistema de Filtros](#sistema-de-filtros)
9. [Reportes y Exportaciones](#reportes-y-exportaciones)
10. [WebSockets y Notificaciones](#websockets-y-notificaciones)
11. [Casos de Uso Detallados](#casos-de-uso-detallados)
12. [Troubleshooting](#troubleshooting)

---

## 1. Introducción y Propósito

### ¿Qué es el Módulo Almacén?

El módulo **Almacén** es el sistema central de gestión de inventarios de Semilla360. Actúa como puente entre el ERP Starsoft (SQL Server) y la aplicación web (MySQL), proporcionando:

- **Sincronización Automática**: Extracción incremental de movimientos desde el ERP
- **Gestión de Stock**: Cálculo en tiempo real de existencias por almacén/producto
- **Transferencias**: Movimientos entre almacenes con estados y trazabilidad
- **Reportes Kardex**: Historial completo de movimientos con saldos acumulados
- **API RESTful**: Endpoints optimizados con filtros avanzados y paginación


### Objetivos Clave

1. **Unificación de Datos**: Consolidar información de 3 empresas (Semilla, Maxi, Trading) en una sola base de datos
2. **Performance**: Reducir latencia mediante caché local (LegacyMovAlm*)
3. **Trazabilidad**: Auditoría completa de movimientos con soft-delete
4. **Automatización**: Sincronización sin intervención manual
5. **Flexibilidad**: API con filtros potentes para consultas personalizadas

### Estadísticas del Módulo

- **Líneas de Código**: ~3,300 líneas Python
- **Modelos**: 12 modelos propios + 4 modelos ERP (managed=False)
- **Endpoints API**: 15+ endpoints con ~50 variaciones de filtros
- **Tareas Asíncronas**: 2 tasks principales (sync incremental + full reconciliation)
- **Reportes**: Kardex en JSON/Excel/PDF

---

## 2. Arquitectura del Módulo

### 2.1 Diagrama de Capas

```
┌────────────────────────────────────────────────────────────────────┐
│                         CAPA DE PRESENTACIÓN                       │
│  Frontend (React/Vue) → API REST → WebSockets (Notificaciones)   │
└────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────┐
│                         CAPA DE APLICACIÓN                         │
│  ViewSets DRF → Serializers → Filtros → Servicios → Paginación   │
└────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────┐
│                         CAPA DE NEGOCIO                            │
│  Models (BaseModel) → Stock.recalcular() → Transferencia.recibir()│
└────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────┐
│                         CAPA DE DATOS                              │
│  MySQL (Semilla360) ←→ SQL Server (ERP Starsoft x3) ←→ Redis      │
└────────────────────────────────────────────────────────────────────┘
                                    ↓
┌────────────────────────────────────────────────────────────────────┐
│                         CAPA DE INFRAESTRUCTURA                    │
│  RQ Workers (Tasks) → Django Channels → ODBC Driver 17             │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 Flujo de Datos (Data Pipeline)

```
[ERP Starsoft - SQL Server]
          ↓ (Sync Task cada X minutos)
  [LegacyMovAlmCab/Det - MySQL Cache]
          ↓ (Mapeo y Normalización)
    [MovimientoAlmacen - Modelo Unificado]
          ↓ (Trigger: recalcular_stock)
       [Stock - Tabla Calculada]
          ↓ (API Query)
     [Frontend - Visualización]
```

### 2.3 Arquitectura de Sincronización

**Estrategia Híbrida: Incremental + Reconciliación**

```python
# Configuración por defecto
SYNC_INTERVAL = "cada 15 minutos"  # Vía RQ Scheduler
RECONCILIATION_DAYS = 30           # Re-procesar últimos 30 días (detección de anulaciones)
START_YEAR = 2000                  # Primera vez: procesar todo desde el año 2000
```

**Lógica de Fechas Inteligente:**

1. **Primera Ejecución (DB vacía)**:
   - `ultima_sync_fecha = 2000-01-01`
   - `fecha_reconciliacion = hoy - 30 días`
   - `fecha_inicio_fase2 = min(2000-01-01, hoy-30) = 2000-01-01`
   - **Resultado**: Procesa TODO el histórico

2. **Ejecuciones Subsecuentes (DB poblada)**:
   - `ultima_sync_fecha = (última fecha procesada exitosamente)`
   - `fecha_reconciliacion = hoy - 30 días`
   - `fecha_inicio_fase2 = min(ultima_sync_fecha, hoy-30)`
   - **Resultado**: Solo procesa nuevos + ventana de seguridad

---

## 3. Modelos de Datos

### 3.1 Modelos ERP (Read-Only, managed=False)

Estos modelos apuntan directamente a las tablas del ERP Starsoft en SQL Server.

#### **MovAlmCab** (MOVALMCAB)

Representa la **cabecera** de un documento de movimiento de almacén.

**Tabla en SQL Server**: `MOVALMCAB`

**Campos Principales:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `caalma` | CharField(2) | Código del almacén (ej: 'AD', 'AL') |
| `catd` | CharField(2) | Tipo de documento (NI, GS, TR, NS, BV) |
| `canumdoc` | CharField(11) | Número del documento (ej: '0000001234') |
| `cafecdoc` | DateTimeField | Fecha del documento |
| `cafecact` | DateTimeField | **Fecha de actualización** (usada para sync incremental) |
| `catipmov` | CharField(1) | Tipo movimiento: 'E'=Entrada, 'S'=Salida |
| `cacodmov` | CharField(2) | Código movimiento (ej: 'CO'=Compra, 'TD'=Transferencia) |
| `casitgui` | CharField(1) | Estado: 'F'=Facturado, 'V'=Venta, 'A'=Anulado |
| `caglosa` | CharField(8000) | Descripción/glosa del movimiento |
| `cacodpro` | CharField(11) | Código del proveedor |
| `canompro` | CharField(100) | Nombre del proveedor |
| `cacodcli` | CharField(11) | Código del cliente |
| `canomcli` | CharField(100) | Nombre del cliente |
| `canumord` | CharField(5000) | Números de orden de compra (puede tener múltiples) |
| `canroimp` | CharField(13) | Número de importación |
| `caimportacion` | BooleanField | ¿Es una importación? |
| `carfalma` | CharField(2) | Almacén de referencia (para transferencias) |
| `carfndoc` | CharField(21) | Número de documento de referencia |
| `motivo_gs` | CharField(50) | Motivo de guía de salida |
| `cadirenv` | CharField(150) | Dirección de envío |

**Clave Primaria Compuesta**: `(caalma, catd, canumdoc)`

**Ejemplo de registro:**
```python
{
    'caalma': 'AD',
    'catd': 'NI',
    'canumdoc': '0000012345',
    'cafecdoc': datetime(2024, 11, 15, 8, 30),
    'catipmov': 'E',
    'cacodmov': 'CO',
    'casitgui': 'F',
    'caglosa': 'COMPRA DE SEMILLAS IMPORTADAS',
    'canompro': 'SEED IMPORTS CHINA LTD',
    'canumord': '000123-000124',
    'caimportacion': True
}
```

#### **MovAlmDet** (MOVALMDET)

Representa cada **línea de detalle** de un documento (cada producto/ítem).

**Tabla en SQL Server**: `MOVALMDET`

**Campos Principales:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `dealma` | CharField(2) | Código del almacén |
| `detd` | CharField(2) | Tipo de documento |
| `denumdoc` | CharField(11) | Número del documento |
| `deitem` | IntegerField | **Número de línea/ítem** (1, 2, 3...) |
| `decodigo` | CharField(20) | **Código del producto** |
| `dedescri` | CharField(200) | Descripción del producto |
| `decantid` | DecimalField(15,6) | **Cantidad** del movimiento |
| `deunidad` | CharField(6) | Unidad de medida (KG, UN, etc.) |
| `depreuni` | DecimalField(15,6) | Precio unitario |
| `devaltot` | DecimalField(15,6) | Valor total (cantidad * precio) |
| `delote` | CharField(45) | Número de lote |
| `deserie` | CharField(45) | Número de serie |
| `deglosa` | CharField(300) | Glosa específica del ítem |
| `detexto` | TextField | Texto adicional (usado para notas largas) |
| `defecdoc` | DateTimeField | Fecha del documento (nivel detalle) |

**Clave Primaria Compuesta**: `(dealma, detd, denumdoc, deitem)`

**Ejemplo de registro:**
```python
{
    'dealma': 'AD',
    'detd': 'NI',
    'denumdoc': '0000012345',
    'deitem': 1,
    'decodigo': 'SEM-MAZ-001',
    'dedescri': 'SEMILLA DE MAIZ HIBRIDO',
    'decantid': Decimal('1500.000000'),
    'deunidad': 'KG',
    'depreuni': Decimal('25.50'),
    'devaltot': Decimal('38250.00'),
    'delote': 'LOT-2024-NOV-001'
}
```

**Nota Importante**: Algunos registros tienen `decodigo = 'TEXTO'`. Estos NO son productos, sino líneas de comentarios/glosas adicionales. Se guardan en `MovimientoAlmacenNota`.

#### **GremisionCab** y **GremisionDet**

Guías de remisión electrónicas (GRE) para traslados. Similar estructura a MovAlm pero con campos específicos de transporte.

**Uso**: Consulta de guías emitidas, validación de transportes, auditoría de traslados.


### 3.2 Modelos Locales (MySQL, managed=True)

Estos modelos se crean y gestionan en la base de datos MySQL de Semilla360.

#### **Almacen**

Catálogo de almacenes/sedes de las empresas.

**Hereda de**: `BaseModel` (soft-delete, auditoría, timestamps)

**Campos Principales:**
```python
empresa = ForeignKey(Empresa)  # Empresa a la que pertenece
codigo = CharField(2)           # 'AD', 'AL', 'AO', etc.
descripcion = CharField(25)     # 'ALMACEN AREQUIPA', 'ALMACEN LIMA', etc.
direccion = CharField(100)      # Dirección física
distrito = CharField(30)
telefono = CharField(10)
ubigeo = CharField(12)          # Código SUNAT
```

**Uso**: Filtrado de movimientos, reportes por sede, transferencias.

#### **LegacyMovAlmCab** y **LegacyMovAlmDet**

**Propósito**: Caché local de los datos del ERP para mejorar el performance.

**Ventajas**:
- ✅ Consultas rápidas (MySQL local vs SQL Server remoto)
- ✅ Reduce carga en el ERP
- ✅ Permite consultas complejas sin afectar producción
- ✅ Histórico completo disponible offline

**Estructura**: Copia 1:1 de MovAlmCab/Det + campo `empresa` para identificar origen.

**Ejemplo de uso en Sync:**
```python
# 1. Extraer de ERP (remoto)
remote_cab = MovAlmCab.objects.using('bd_semilla_starsoft').filter(...)

# 2. Guardar en cache local (MySQL)
LegacyMovAlmCab.objects.update_or_create(
    empresa=empresa,
    caalma=cab.caalma,
    catd=cab.catd,
    canumdoc=cab.canumdoc,
    defaults={...todos_los_campos...}
)

# 3. Luego, mapear a MovimientoAlmacen (normalizado)
```

#### **MovimientoAlmacen**

**El modelo central del sistema**. Representa un movimiento unificado de inventario.

**Hereda de**: `BaseModel`

**Campos Principales:**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **Relaciones** |
| `empresa` | ForeignKey | Empresa (Semilla, Maxi, Trading) |
| `almacen` | ForeignKey | Almacén donde ocurrió el movimiento |
| `producto` | ForeignKey | Producto movido |
| **Identificadores ERP** |
| `id_erp_cab` | CharField(50) | PK del documento en ERP: "AD-NI-0000123" |
| `id_erp_det` | CharField(60) | PK del detalle: "AD-NI-0000123-1" |
| `tipo_documento_erp` | CharField(2) | NI, GS, TR, NS, BV, NC, FT |
| `numero_documento_erp` | CharField(11) | Número del doc en ERP |
| `item_erp` | IntegerField | Número de línea (DEITEM) |
| **Datos del Movimiento** |
| `fecha_documento` | DateTimeField | Fecha del documento |
| `fecha_movimiento` | DateTimeField | Fecha de actualización (para ordenamiento) |
| `cantidad` | DecimalField(15,6) | Cantidad movida |
| `unidad_medida_erp` | CharField(6) | KG, UN, LT, etc. |
| `costo_unitario` | DecimalField(15,6) | Costo por unidad |
| `valor_total` | DecimalField(15,6) | cantidad * costo_unitario |
| **Clasificación** |
| `es_ingreso` | BooleanField | True=NI, False=GS/TR |
| `estado_erp` | CharField(1) | 'F', 'V', 'A', 'P' |
| `codigo_movimiento` | CharField(10) | 'CO', 'TD', 'FT', 'VE', etc. |
| **Entidades** |
| `proveedor_erp_id` | CharField(15) | Código del proveedor |
| `nombre_proveedor` | CharField(100) | Nombre del proveedor |
| `cliente_erp_id` | CharField(15) | Código del cliente |
| `cliente_erp_nombre` | CharField(100) | Nombre del cliente |
| **Referencias** |
| `numero_orden_compra` | TextField | OC asociadas (puede tener múltiples) |
| `referencia_documento` | CharField(25) | Documento de referencia |
| `almacen_ref` | CharField(10) | Almacén de origen (transferencias) |
| `id_importacion` | CharField(20) | Número de importación |
| `importacion` | BooleanField | ¿Es importación? |
| **Detalles** |
| `glosa_cabecera` | TextField | Descripción del documento |
| `glosa_detalle` | TextField | Descripción del ítem |
| `motivo_tras` | CharField(100) | Motivo de traslado |
| `direccion_envio_erp` | CharField(100) | Dirección de destino |
| `lote` | CharField(50) | Lote del producto |
| `serie` | CharField(50) | Serie del producto |
| **Otros** |
| `sede_facturacion` | ForeignKey(Almacen) | Sede para reportes GV |
| `cantidad_bultos` | DecimalField(15,2) | Cantidad de bultos/sacos |

**Constraints**:
```python
UniqueConstraint(fields=['empresa', 'id_erp_det'], name='unique_erp_detail_movement')
```
Garantiza que no haya duplicados por empresa.

**Índices** (para performance):
```python
Index(['empresa', 'almacen', 'producto', 'fecha_documento'])
Index(['proveedor_erp_id'])
Index(['cliente_erp_id'])
Index(['estado_erp'])
Index(['es_ingreso'])
```

**Propiedad Calculada: `descripcion_visual`**

Genera una descripción inteligente basada en el tipo de movimiento:

```python
@property
def descripcion_visual(self):
    cod_mov = self.codigo_movimiento.upper() if self.codigo_movimiento else ""
    
    if cod_mov == 'TD':  # Transferencia
        return self.glosa_cabecera or f"TRANSFERENCIA ENTRE ALMACENES - {self.almacen_ref}"
    
    elif cod_mov == 'FT':  # Flete
        return f"INGRESO POR FLETE - {self.glosa_cabecera}"
    
    else:  # Normal (Compra/Venta)
        entidad = self.nombre_proveedor if self.es_ingreso else self.cliente_erp_nombre
        return f"{entidad} - {self.glosa_cabecera}"
```

**Ejemplo de uso:**
```python
# Consultar movimientos de un producto en un almacén
movs = MovimientoAlmacen.objects.filter(
    empresa_id=1,
    almacen__codigo='AD',
    producto__codigo_producto='SEM-MAZ-001',
    fecha_documento__gte='2024-01-01',
    state=True
).select_related('empresa', 'almacen', 'producto')

for m in movs:
    print(f"{m.fecha_documento} | {m.tipo_documento_erp}-{m.numero_documento_erp} | {m.descripcion_visual} | {m.cantidad}")
```

#### **MovimientoAlmacenNota**

Almacena las **líneas de texto** del ERP (donde `DECODIGO='TEXTO'`).

**¿Por qué existe?**: En el ERP, algunos documentos tienen líneas de detalle que NO son productos, sino comentarios o glosas extendidas. Estas se separan en esta tabla para no contaminar MovimientoAlmacen.

**Campos**:
```python
empresa = ForeignKey(Empresa)
id_erp_cab = CharField(50)        # Documento al que pertenece
id_erp_det = CharField(60)        # ID único de la línea
item_erp = IntegerField           # Número de línea
texto_descripcion = TextField     # DEDESCRI del ERP
texto_detalle = TextField         # DETEXTO del ERP
```

**Uso**: Se consultan junto con MovimientoAlmacen para mostrar notas adicionales en el Kardex.

#### **Stock**

Tabla **calculada** que almacena el stock actual de cada producto por almacén.

**NO hereda de BaseModel** (no necesita soft-delete ni auditoría).

**Campos**:
```python
empresa = ForeignKey(Empresa)
almacen = ForeignKey(Almacen)
producto = ForeignKey(Producto)
cantidad_actual = DecimalField(15,6)        # Stock físico
cantidad_en_transito = DecimalField(15,6)   # Stock en transferencias pendientes
fecha_ultimo_movimiento = DateTimeField     # Última actualización
```

**Unique Constraint**: `(empresa, almacen, producto)`

**Método Clave: `recalcular_stock_completo()`**

Recalcula el stock desde cero basándose en MovimientoAlmacen:

```python
@staticmethod
def recalcular_stock_completo(empresa_id, almacen_id, producto_id):
    """
    1. Suma ingresos de MovimientoAlmacen (es_ingreso=True)
    2. Resta salidas de MovimientoAlmacen (es_ingreso=False)
    3. Calcula en_transito desde Transferencia (estado='EN_TRANSITO')
    4. Guarda resultado en Stock
    """
    agregado = MovimientoAlmacen.objects.filter(
        empresa_id=empresa_id,
        almacen_id=almacen_id,
        producto_id=producto_id,
        state=True
    ).aggregate(
        ingresos=Coalesce(Sum('cantidad', filter=Q(es_ingreso=True)), 0),
        salidas=Coalesce(Sum('cantidad', filter=Q(es_ingreso=False)), 0)
    )
    
    stock_actual = agregado['ingresos'] - agregado['salidas']
    
    en_transito = Transferencia.objects.filter(
        empresa_id=empresa_id,
        almacen_origen_id=almacen_id,
        producto_id=producto_id,
        estado='EN_TRANSITO'
    ).aggregate(total=Coalesce(Sum('cantidad_enviada'), 0))['total']
    
    Stock.objects.update_or_create(
        empresa_id=empresa_id,
        almacen_id=almacen_id,
        producto_id=producto_id,
        defaults={
            'cantidad_actual': stock_actual,
            'cantidad_en_transito': en_transito,
            'fecha_ultimo_movimiento': timezone.now()
        }
    )
```

**¿Cuándo se recalcula?**
- ✅ Después de cada sincronización con el ERP
- ✅ Al recibir una transferencia
- ✅ Al revertir una transferencia
- ✅ Manualmente vía endpoint `/api/almacen/stock/recalcular/`

#### **Transferencia**

Gestiona traslados de mercancía entre almacenes con **máquina de estados**.

**Hereda de**: `BaseModel`

**Estados Posibles**:
```python
ESTADOS = [
    ('EN_TRANSITO', 'En Tránsito'),            # GS emitida, NI pendiente
    ('RECIBIDO', 'Recibido Completo'),         # NI confirmada, cantidad exacta
    ('RECIBIDO_PARCIAL', 'Recibido Parcial'),  # NI con merma
    ('RECIBIDO_SOBRANTE', 'Recibido Sobrante'), # NI con exceso (raro)
    ('PERDIDO', 'Pérdida Total'),              # NI con cantidad = 0
]
```

**Campos**:
```python
empresa = ForeignKey(Empresa)
almacen_origen = ForeignKey(Almacen)
almacen_destino = ForeignKey(Almacen)
producto = ForeignKey(Producto)

# IDs del ERP
id_erp_salida_det = CharField(60)   # PK del detalle de GS
id_erp_ingreso_det = CharField(60)  # PK del detalle de NI (cuando se recibe)
id_erp_salida_cab = CharField(50)
id_erp_ingreso_cab = CharField(50)

# Cantidades
cantidad_enviada = DecimalField(15,6)
cantidad_recibida = DecimalField(15,6, null=True)
cantidad_diferencia = DecimalField(15,6, null=True)

# Fechas y Estado
estado = CharField(20, choices=ESTADOS, default='EN_TRANSITO')
fecha_envio = DateTimeField
fecha_recepcion = DateTimeField(null=True)
notas_recepcion = TextField(null=True)
```

**Métodos Principales**:

**1. `recibir_mercaderia(cantidad_recibida, fecha_recepcion, notas, auto_recepcion=False)`**

Procesa la recepción de una transferencia:

```python
def recibir_mercaderia(self, cantidad_recibida, fecha_recepcion, notas='', auto_recepcion=False):
    """
    1. Valida que esté EN_TRANSITO
    2. Calcula diferencia (recibida - enviada)
    3. Determina nuevo estado (RECIBIDO, PARCIAL, SOBRANTE, PERDIDO)
    4. Crea MovimientoAlmacen de ingreso (NI) en almacen_destino
    5. Recalcula stock en ambos almacenes
    """
    if self.estado != 'EN_TRANSITO':
        return False
    
    diferencia = cantidad_recibida - self.cantidad_enviada
    
    # Actualizar campos
    self.cantidad_recibida = cantidad_recibida
    self.cantidad_diferencia = diferencia
    self.fecha_recepcion = fecha_recepcion
    self.notas_recepcion = notas
    
    # Determinar estado
    if cantidad_recibida <= 0:
        self.estado = 'PERDIDO'
    elif diferencia > 0:
        self.estado = 'RECIBIDO_SOBRANTE'
    elif diferencia < 0:
        self.estado = 'RECIBIDO_PARCIAL'
    else:
        self.estado = 'RECIBIDO'
    
    self.save()
    
    # Crear MovimientoAlmacen de ingreso
    MovimientoAlmacen.objects.update_or_create(
        empresa=self.empresa,
        id_erp_det=self.id_erp_ingreso_det or f"WEB-TR-{self.id}-IN",
        defaults={
            'almacen': self.almacen_destino,
            'producto': self.producto,
            'cantidad': cantidad_recibida,
            'es_ingreso': True,
            'tipo_documento_erp': 'NI',
            # ... más campos ...
        }
    )
    
    # Recalcular stock
    transaction.on_commit(lambda: self._disparar_recalculo_stock())
    
    return True
```

**2. `revertir_recepcion()`**

Revierte una recepción errónea:

```python
def revertir_recepcion(self):
    """
    1. Valida que NO esté EN_TRANSITO
    2. ELIMINA el MovimientoAlmacen de ingreso creado
    3. Restablece estado a EN_TRANSITO
    4. Recalcula stock
    """
    if self.estado == 'EN_TRANSITO':
        return False
    
    # Eliminar el movimiento de ingreso
    id_bussines_key = self.id_erp_ingreso_det or f"WEB-TR-{self.id}-IN"
    MovimientoAlmacen.objects.filter(
        empresa=self.empresa,
        id_erp_det=id_bussines_key
    ).delete()
    
    # Restablecer estado
    self.estado = 'EN_TRANSITO'
    self.cantidad_recibida = None
    self.cantidad_diferencia = None
    self.fecha_recepcion = None
    self.notas_recepcion = f"Recepción revertida por usuario el {timezone.now()}."
    
    self.save()
    
    # Recalcular stock
    transaction.on_commit(lambda: self._disparar_recalculo_stock())
    
    return True
```

**Flujo de Vida de una Transferencia:**

```
1. ERP emite GS (Guía de Salida) → Sync crea Transferencia con estado EN_TRANSITO
   - Se crea MovimientoAlmacen de salida (es_ingreso=False) en almacen_origen
   - Stock origen disminuye
   - cantidad_en_transito aumenta

2. Usuario recibe mercancía → Llama a recibir_mercaderia()
   - Si sync ya vinculó NI del ERP, usa datos reales
   - Si no, usa datos ingresados manualmente
   - Se crea MovimientoAlmacen de ingreso (es_ingreso=True) en almacen_destino
   - Stock destino aumenta
   - cantidad_en_transito disminuye
   - Estado cambia a RECIBIDO/PARCIAL/SOBRANTE

3. Si hubo error → Llama a revertir_recepcion()
   - Vuelve a EN_TRANSITO
   - Se elimina MovimientoAlmacen de ingreso
   - Stock se recalcula
```

#### **GastoDocumentoAlmacen**

Registra gastos asociados a documentos de movimiento (ej: estibaje en guías de salida).

**Hereda de**: `BaseModel`

**Campos**:
```python
empresa = ForeignKey(Empresa)
id_erp_cab = CharField(50)          # Documento al que pertenece
tipo_gasto = CharField(3)           # 'EST', 'TRN', 'SEG', 'OTR'
descripcion = TextField
monto = DecimalField(12,2)
fecha_gasto = DateField
```

**Uso**: Reportes de costos adicionales, facturación, contabilidad.

#### **ControlSyncMovAlmacen**

Control de sincronización por empresa.

**Campos**:
```python
empresa = OneToOneField(Empresa)
ultima_fecha = DateTimeField        # Última fecha procesada (CAFECACT)
last_full_sync_run = DateTimeField  # Última reconciliación completa
```

**Uso**: El sistema de sync consulta este registro para saber desde qué fecha extraer datos.

---

## 4. Sistema de Sincronización

### 4.1 Tarea Principal: `sincronizar_empresa_erp_task()`

**Ubicación**: `almacen/tasks.py`

**Decorador**: `@job('default', timeout=7200)`  # 2 horas max

**Parámetros**:
```python
def sincronizar_empresa_erp_task(
    empresa_alias,           # 'bd_semilla_starsoft', 'bd_maxi_starsoft', etc.
    start_year=2000,         # Año inicial para primera carga
    reconciliation_days=30,  # Días hacia atrás para re-procesar
    user_id=None            # ID del usuario que disparó el sync (para WebSockets)
):
```

### 4.2 Fases de la Sincronización

**FASE 1: EXTRACCIÓN (ERP → LegacyMovAlm)**

1. **Determinar rango de fechas**:
   ```python
   ultima_sync_fecha = control_sync.ultima_fecha or fecha_start_year
   fecha_reconciliacion = ahora - timedelta(days=reconciliation_days)
   fecha_inicio_fase1 = ultima_sync_fecha
   ```

2. **Consultar MovAlmCab en SQL Server**:
   ```python
   qs_base = MovAlmCab.objects.using(db_alias).filter(
       Q(cafecdoc__gte=ultima_sync_fecha),
       catd__in=['NI', 'GS', 'TR', 'TK', 'NS', 'BV', 'NC', 'FT']
   ).order_by('cafecdoc')
   ```

3. **Procesar en batches de 50**:
   ```python
   for page in paginator.page_range:
       batch_records = page.object_list
       
       # Prefetch masivo de detalles
       q_filters = Q()
       for cab in batch_records:
           q_filters |= Q(dealma=cab.caalma, detd=cab.catd, denumdoc=cab.canumdoc)
       
       remote_details = MovAlmDet.objects.using(db_alias).filter(q_filters)
       
       # Guardar en LegacyMovAlmCab/Det (MySQL)
       with transaction.atomic():
           for cab in batch_records:
               LegacyMovAlmCab.objects.update_or_create(...)
               
               for det in grouped_details[key]:
                   LegacyMovAlmDet.objects.update_or_create(...)
   ```

4. **Actualizar control_sync.ultima_fecha**

**FASE 2: NORMALIZACIÓN (LegacyMovAlm → MovimientoAlmacen)**

1. **Determinar rango de fechas**:
   ```python
   fecha_inicio_fase2 = min(ultima_sync_fecha, fecha_reconciliacion)
   ```
   Esto asegura re-procesar los últimos 30 días para detectar anulaciones.

2. **Consultar LegacyMovAlmDet desde MySQL**:
   ```python
   legacy_dets = LegacyMovAlmDet.objects.filter(
       empresa=empresa,
       defecdoc__gte=fecha_inicio_fase2
   ).select_related('empresa').order_by('defecdoc')
   ```

3. **Mapear y crear MovimientoAlmacen**:
   ```python
   for det in legacy_dets:
       # Buscar cabecera
       try:
           cab = LegacyMovAlmCab.objects.get(...)
       except LegacyMovAlmCab.DoesNotExist:
           continue
       
       # Validar si es producto o nota
       if det.decodigo == 'TEXTO':
           # Guardar en MovimientoAlmacenNota
           MovimientoAlmacenNota.objects.update_or_create(...)
           continue
       
       # Buscar producto
       try:
           producto = Producto.objects.get(
               empresa=empresa,
               codigo_producto=det.decodigo
           )
       except Producto.DoesNotExist:
           # Crear producto automáticamente
           producto = Producto.objects.create(...)
       
       # Buscar almacén
       try:
           almacen = Almacen.objects.get(empresa=empresa, codigo=cab.caalma)
       except Almacen.DoesNotExist:
           # Crear almacén automáticamente
           almacen = Almacen.objects.create(...)
       
       # Construir ID único
       id_erp_cab = f"{cab.caalma}-{cab.catd}-{cab.canumdoc}"
       id_erp_det = f"{det.dealma}-{det.detd}-{det.denumdoc}-{det.deitem}"
       
       # Crear/Actualizar MovimientoAlmacen
       MovimientoAlmacen.objects.update_or_create(
           empresa=empresa,
           id_erp_det=id_erp_det,
           defaults={
               'id_erp_cab': id_erp_cab,
               'almacen': almacen,
               'producto': producto,
               'tipo_documento_erp': cab.catd,
               'numero_documento_erp': det.denumdoc,
               'item_erp': det.deitem,
               'fecha_documento': cab.cafecdoc,
               'fecha_movimiento': cab.cafecact or cab.cafecdoc,
               'cantidad': det.decantid,
               'es_ingreso': (cab.catipmov == 'E'),
               'estado_erp': cab.casitgui,
               # ... mapeo completo de todos los campos ...
           }
       )
   ```

**FASE 3: DETECCIÓN DE TRANSFERENCIAS**

1. **Vincular GS con NI**:
   ```python
   # Buscar GS sin NI vinculada (EN_TRANSITO)
   movs_gs = MovimientoAlmacen.objects.filter(
       tipo_documento_erp='GS',
       codigo_movimiento='TD',
       # Que NO tengan transferencia creada
   )
   
   for gs in movs_gs:
       # Crear Transferencia
       transferencia = Transferencia.objects.create(
           empresa=gs.empresa,
           almacen_origen=gs.almacen,
           almacen_destino=almacen_ref,  # Del campo carfalma
           producto=gs.producto,
           cantidad_enviada=gs.cantidad,
           id_erp_salida_det=gs.id_erp_det,
           id_erp_salida_cab=gs.id_erp_cab,
           estado='EN_TRANSITO',
           fecha_envio=gs.fecha_documento
       )
   
   # Buscar NI que correspondan a GS (auto-recepción)
   movs_ni = MovimientoAlmacen.objects.filter(
       tipo_documento_erp='NI',
       codigo_movimiento='TD',
       referencia_documento__isnull=False
   )
   
   for ni in movs_ni:
       # Buscar transferencia por referencia
       try:
           transferencia = Transferencia.objects.get(
               id_erp_salida_cab__contains=ni.referencia_documento,
               estado='EN_TRANSITO'
           )
           
           # Auto-recibir
           transferencia.recibir_mercaderia(
               cantidad_recibida=ni.cantidad,
               fecha_recepcion=ni.fecha_documento,
               notas="Auto-recepción por sync ERP",
               auto_recepcion=True
           )
       except Transferencia.DoesNotExist:
           pass
   ```

**FASE 4: RECÁLCULO DE STOCK**

1. **Obtener productos únicos sincronizados**:
   ```python
   productos_afectados = MovimientoAlmacen.objects.filter(
       empresa=empresa,
       fecha_documento__gte=fecha_inicio_fase2
   ).values_list('producto_id', 'almacen_id').distinct()
   ```

2. **Recalcular stock para cada combinación**:
   ```python
   for producto_id, almacen_id in productos_afectados:
       Stock.recalcular_stock_completo(empresa.id, almacen_id, producto_id)
   ```

### 4.3 Notificaciones en Tiempo Real

Durante cada fase, el sistema envía notificaciones por WebSocket:

```python
# Inicio
notificar_grupo_empresa(empresa.id, 'started', 'Iniciando Sincronización...')

# Fase 1
notificar_grupo_empresa(empresa.id, 'running_f1', f'Fase 1: {processed}/{total} documentos')

# Fase 2
notificar_grupo_empresa(empresa.id, 'running_f2', f'Fase 2: {processed}/{total} movimientos')

# Fase 3
notificar_grupo_empresa(empresa.id, 'running_f3', f'Fase 3: Vinculando transferencias...')

# Fase 4
notificar_grupo_empresa(empresa.id, 'running_f4', f'Fase 4: Recalculando {len(productos)} stocks...')

# Fin
notificar_grupo_empresa(empresa.id, 'completed', f'Sincronización completada.', result={...})
```

### 4.4 Progreso en Redis

El progreso también se guarda en Redis para sobrevivir a recargas de página (F5):

```python
def actualizar_progreso_job(percent_float, msg):
    job = get_current_job()
    if job:
        job.meta['progress_percent'] = percent_float
        job.meta['progress_message'] = msg
        job.save_meta()
```

El frontend puede consultar `/api/almacen/check-sync-status/` para recuperar el progreso.

### 4.5 Manejo de Errores

```python
try:
    # ... lógica de sincronización ...
except Exception as e:
    logger.error(f"Error en sync: {e}", exc_info=True)
    notificar_grupo_empresa(empresa.id, 'error', f'Error: {str(e)}')
    return f"Error: {str(e)}"
```

Los errores se loggean en `logs/rq_tasks.log`.



---

## 5. API Endpoints

### 5.1 Resumen de Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/almacen/empresas/` | GET, POST, PUT, DELETE | CRUD de empresas |
| `/api/almacen/almacenes/` | GET, POST, PUT, DELETE | CRUD de almacenes |
| `/api/almacen/productos/` | GET, POST, PUT, DELETE | CRUD de productos |
| `/api/almacen/movimientos/` | GET | Listado de movimientos (solo lectura) |
| `/api/almacen/movimiento-notas/` | GET | Notas de movimientos |
| `/api/almacen/stock/` | GET | Stock actual por almacén/producto |
| `/api/almacen/transferencias/` | GET | Listado de transferencias |
| `/api/almacen/transferencias/{id}/` | GET | Detalle de transferencia |
| `/api/almacen/transferencias/{id}/recibir/` | POST | Recibir mercancía |
| `/api/almacen/transferencias/{id}/revertir_recepcion/` | POST | Revertir recepción |
| `/api/almacen/trigger-sync/` | POST | Iniciar sincronización |
| `/api/almacen/check-sync-status/` | GET | Consultar estado de sync |
| `/api/almacen/reporte-kardex/` | GET | Reporte Kardex (JSON/Excel/PDF) |
| `/api/almacen/gremisiones/` | GET | Guías de remisión electrónicas |
| `/api/almacen/consulta-guia/` | GET | Consultar guía específica |

### 5.2 Endpoints Detallados

#### **GET /api/almacen/movimientos/**

Lista movimientos de almacén con filtros avanzados y paginación.

**Filtros Disponibles:**

```python
# Filtros exactos
?empresa=1                          # Por empresa
?almacen=2                          # Por almacén
?producto=123                       # Por producto
?producto__in=123,124,125           # Múltiples productos
?tipo_documento_erp=NI              # Por tipo de documento
?tipo_documento_erp__in=NI,GS       # Múltiples tipos
?es_ingreso=true                    # Solo ingresos (o false para salidas)
?proveedor_erp_id=P001              # Por proveedor
?cliente_erp_id=C001                # Por cliente

# Filtros de rango de fecha
?fecha_documento_desde=2024-01-01   # Desde fecha (inclusive)
?fecha_documento_hasta=2024-12-31   # Hasta fecha (inclusive)

# Búsqueda global (busca en múltiples campos)
?search=SEM-MAZ                     # Busca en: número doc, nombre producto, OC, referencia, cliente

# Búsqueda específica
?numero_documento=0001234           # Por número de documento (parcial)
?orden_compra=000123                # Por orden de compra (parcial)

# Ordenamiento
?ordering=fecha_documento           # Ascendente
?ordering=-fecha_documento          # Descendente
?ordering=producto__nombre_producto # Por nombre de producto

# Paginación
?page=1                             # Página
?page_size=50                       # Registros por página (default: 30, max: 100)
```

**Ejemplo de Request:**
```bash
GET /api/almacen/movimientos/?empresa=1&almacen=2&fecha_documento_desde=2024-11-01&es_ingreso=true&ordering=-fecha_documento&page_size=50
```

**Ejemplo de Response:**
```json
{
  "count": 1234,
  "next": "http://localhost:8000/api/almacen/movimientos/?page=2",
  "previous": null,
  "results": [
    {
      "id": 12345,
      "empresa": {
        "id": 1,
        "razon_social": "GRUPO LA SEMILLA S.A.",
        "nombre_empresa": "bd_semilla_starsoft"
      },
      "almacen": {
        "id": 2,
        "codigo": "AD",
        "descripcion": "ALMACEN AREQUIPA"
      },
      "producto": {
        "id": 123,
        "codigo_producto": "SEM-MAZ-001",
        "nombre_producto": "SEMILLA DE MAIZ HIBRIDO"
      },
      "id_erp_cab": "AD-NI-0001234",
      "id_erp_det": "AD-NI-0001234-1",
      "tipo_documento_erp": "NI",
      "numero_documento_erp": "0001234",
      "item_erp": 1,
      "fecha_documento": "2024-11-15T08:30:00Z",
      "fecha_movimiento": "2024-11-15T14:20:00Z",
      "cantidad": "1500.000000",
      "unidad_medida_erp": "KG",
      "costo_unitario": "25.500000",
      "valor_total": "38250.000000",
      "es_ingreso": true,
      "estado_erp": "F",
      "codigo_movimiento": "CO",
      "proveedor_erp_id": "P00001",
      "nombre_proveedor": "SEED IMPORTS CHINA LTD",
      "cliente_erp_id": null,
      "cliente_erp_nombre": null,
      "numero_orden_compra": "000123-000124",
      "referencia_documento": null,
      "almacen_ref": null,
      "id_importacion": "IMP-2024-001",
      "importacion": true,
      "glosa_cabecera": "COMPRA DE SEMILLAS IMPORTADAS",
      "glosa_detalle": "LOTE: LOT-2024-NOV-001",
      "motivo_tras": null,
      "direccion_envio_erp": null,
      "lote": "LOT-2024-NOV-001",
      "serie": null,
      "cantidad_bultos": "30.00",
      "notas": [
        {
          "item_erp": 2,
          "texto_descripcion": "CERTIFICADO FITOSANITARIO ADJUNTO",
          "texto_detalle": "Válido hasta 2025-05-15"
        }
      ],
      "state": true,
      "created_date": "2024-11-15T14:25:00Z",
      "modified_date": "2024-11-15T14:25:00Z"
    },
    // ... más movimientos ...
  ]
}
```

**Optimizaciones de Performance:**
- ✅ `select_related('empresa', 'almacen', 'producto')` para evitar N+1 queries
- ✅ Paginación por defecto (30 registros)
- ✅ Prefetch de notas en una sola query para toda la página
- ✅ Índices en campos de filtro frecuente

#### **GET /api/almacen/stock/**

Consulta stock actual calculado.

**Filtros:**
```python
?empresa=1                  # Por empresa (requerido en muchos casos)
?almacen=2                  # Por almacén
?producto=123               # Por producto específico
?search=MAIZ                # Busca en código o nombre de producto
?solo_con_stock=true        # Solo productos con stock > 0
?ordering=cantidad_actual   # Ordenar por cantidad
```

**Response:**
```json
{
  "count": 50,
  "results": [
    {
      "id": 1,
      "empresa": {
        "id": 1,
        "razon_social": "GRUPO LA SEMILLA S.A."
      },
      "almacen": {
        "id": 2,
        "codigo": "AD",
        "descripcion": "ALMACEN AREQUIPA"
      },
      "producto": {
        "id": 123,
        "codigo_producto": "SEM-MAZ-001",
        "nombre_producto": "SEMILLA DE MAIZ HIBRIDO"
      },
      "cantidad_actual": "15000.000000",
      "cantidad_en_transito": "2000.000000",
      "fecha_ultimo_movimiento": "2024-11-15T14:25:00Z"
    }
  ]
}
```

#### **GET /api/almacen/transferencias/**

Lista transferencias entre almacenes.

**Filtros:**
```python
?estado=EN_TRANSITO         # Por estado
?almacen_origen=2           # Por almacén origen
?almacen_destino=3          # Por almacén destino
?fecha_envio__gte=2024-01-01  # Desde fecha
?fecha_envio__lte=2024-12-31  # Hasta fecha
?search=SEM-MAZ             # Busca en código producto o ID ERP
?ordering=-fecha_envio      # Ordenar
```

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "empresa": {...},
      "almacen_origen": {
        "id": 2,
        "codigo": "AD",
        "descripcion": "ALMACEN AREQUIPA"
      },
      "almacen_destino": {
        "id": 3,
        "codigo": "AL",
        "descripcion": "ALMACEN LIMA"
      },
      "producto": {...},
      "id_erp_salida_det": "AD-GS-0005678-1",
      "id_erp_ingreso_det": null,
      "id_erp_salida_cab": "AD-GS-0005678",
      "id_erp_ingreso_cab": null,
      "cantidad_enviada": "500.000000",
      "cantidad_recibida": null,
      "cantidad_diferencia": null,
      "estado": "EN_TRANSITO",
      "fecha_envio": "2024-11-10T10:00:00Z",
      "fecha_recepcion": null,
      "notas_recepcion": null
    }
  ]
}
```

#### **POST /api/almacen/transferencias/{id}/recibir/**

Recibe mercancía de una transferencia EN_TRANSITO.

**Request Body:**
```json
{
  "cantidad_recibida": 495.50,
  "notas_recepcion": "Recibido con merma de 4.5 KG"
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "estado": "RECIBIDO_PARCIAL",
  "cantidad_enviada": "500.000000",
  "cantidad_recibida": "495.500000",
  "cantidad_diferencia": "-4.500000",
  "fecha_recepcion": "2024-11-15T16:30:00Z",
  "notas_recepcion": "Recibido con merma de 4.5 KG",
  // ... resto de campos ...
}
```

**Errores:**
- `400`: Transferencia ya procesada (no está EN_TRANSITO)
- `404`: Transferencia no encontrada
- `500`: Error interno al procesar

#### **POST /api/almacen/transferencias/{id}/revertir_recepcion/**

Revierte una recepción errónea y vuelve la transferencia a EN_TRANSITO.

**Request Body:** (vacío)

**Response (200 OK):**
```json
{
  "id": 1,
  "estado": "EN_TRANSITO",
  "cantidad_recibida": null,
  "cantidad_diferencia": null,
  "fecha_recepcion": null,
  "notas_recepcion": "Recepción revertida por usuario el 2024-11-15 17:00:00"
}
```

#### **POST /api/almacen/trigger-sync/**

Dispara una sincronización manual con el ERP.

**Autenticación**: Requerida (`IsAuthenticated`)

**Request Body:**
```json
{
  "empresa_alias": "bd_semilla_starsoft",
  "start_year": 2020,
  "days": 30
}
```

**Response (202 ACCEPTED):**
```json
{
  "status": "Sincronización iniciada para bd_semilla_starsoft.",
  "job_id": "83fa7c8a-1234-5678-90ab-cdef12345678"
}
```

**Notas:**
- La tarea se ejecuta en background (RQ Worker)
- El progreso se puede consultar con `/api/almacen/check-sync-status/`
- Notificaciones en tiempo real vía WebSocket

#### **GET /api/almacen/check-sync-status/**

Consulta el estado de una sincronización en progreso.

**Autenticación**: Requerida

**Response (Sin sync activo):**
```json
{
  "is_syncing": false
}
```

**Response (Sync en progreso):**
```json
{
  "is_syncing": true,
  "message": "Fase 2: Procesando movimientos... 450/1234",
  "percent": 36.5
}
```

**Lógica interna:**
1. Consulta Redis por jobs del usuario actual
2. Filtra por función `almacen.tasks.sincronizar_empresa_erp_task`
3. Devuelve progreso desde `job.meta`

#### **GET /api/almacen/reporte-kardex/**

Genera reporte Kardex detallado con saldos.

**Parámetros:**
```python
# Requeridos
?empresa_id=1
?almacen_id=2
?producto_id=123                    # O múltiples: ?producto_id=123&producto_id=124
?fecha_inicio=2024-01-01
?fecha_fin=2024-12-31

# Opcional
?export_format=excel                # 'excel' o 'pdf' (omitir para JSON)
```

**Response JSON (default):**
```json
{
  "123": {
    "codigo_producto": "SEM-MAZ-001",
    "nombre_producto": "SEMILLA DE MAIZ HIBRIDO",
    "stock_en_transito": "2000.000000",
    "kardex": [
      {
        "fecha": "2024-01-01",
        "doc": "SALDO ANTERIOR",
        "entrada": 0,
        "salida": 0,
        "saldo": "10000.000000",
        "detalle": "---"
      },
      {
        "fecha": "2024-01-05T08:30:00Z",
        "doc": "NI-0000123",
        "ref": "OC-0000456",
        "entrada": "5000.000000",
        "salida": 0,
        "saldo": "15000.000000",
        "detalle": "SEED IMPORTS CHINA LTD - COMPRA IMPORTACION",
        "origen": "ERP"
      },
      {
        "fecha": "2024-01-10T14:20:00Z",
        "doc": "GS-0000789",
        "ref": null,
        "entrada": 0,
        "salida": "2000.000000",
        "saldo": "13000.000000",
        "detalle": "CLIENTE ABC S.A.C. - VENTA LOCAL",
        "origen": "ERP"
      },
      // ... más movimientos ...
    ]
  },
  "124": {
    // ... otro producto ...
  }
}
```

**Response Excel:** Archivo `.xlsx` descargable con formato profesional.

**Response PDF:** Archivo `.pdf` generado con WeasyPrint.

---

## 6. Funcionalidades Principales

### 6.1 Sincronización Automática

**Scheduler RQ** (configurado por el usuario):

```python
# En producción, usar RQ Scheduler
import django_rq
scheduler = django_rq.get_scheduler('default')

# Programar sincronización cada 15 minutos
scheduler.schedule(
    scheduled_time=timezone.now(),
    func='almacen.tasks.sincronizar_empresa_erp_task',
    args=['bd_semilla_starsoft'],
    kwargs={'start_year': 2020, 'reconciliation_days': 30},
    interval=900,  # 15 minutos
    repeat=None    # Infinito
)
```

### 6.2 Auto-Recepción de Transferencias

El sistema detecta automáticamente cuando una NI (Nota de Ingreso) corresponde a una GS (Guía de Salida) y completa la transferencia:

**Lógica:**
```python
# Durante Fase 3 del sync
movs_ni_transferencia = MovimientoAlmacen.objects.filter(
    tipo_documento_erp='NI',
    codigo_movimiento='TD',
    referencia_documento__isnull=False
)

for ni in movs_ni_transferencia:
    # Buscar transferencia pendiente por referencia
    try:
        transferencia = Transferencia.objects.get(
            empresa=ni.empresa,
            id_erp_salida_cab=ni.referencia_documento,
            estado='EN_TRANSITO'
        )
        
        # Auto-recibir
        transferencia.recibir_mercaderia(
            cantidad_recibida=ni.cantidad,
            fecha_recepcion=ni.fecha_documento,
            notas="Auto-recepción por sincronización ERP",
            auto_recepcion=True
        )
        
    except Transferencia.DoesNotExist:
        pass  # No hay transferencia pendiente
```

### 6.3 Cálculo de Stock en Tiempo Real

**Trigger:** Después de cada sincronización y al recibir/revertir transferencias.

**Método:** `Stock.recalcular_stock_completo(empresa_id, almacen_id, producto_id)`

**Fórmula:**
```
stock_actual = Σ(ingresos) - Σ(salidas)

donde:
  ingresos = MovimientoAlmacen con es_ingreso=True y state=True
  salidas = MovimientoAlmacen con es_ingreso=False y state=True

stock_en_transito = Σ(Transferencia con estado='EN_TRANSITO' y almacen_origen=X)
```

### 6.4 Generación de Reportes Kardex

El servicio `get_kardex_detallado()` genera el reporte siguiendo estos pasos:

1. **Calcular Saldo Anterior:**
   ```python
   saldo_inicial = Σ(ingresos antes de fecha_inicio) - Σ(salidas antes de fecha_inicio)
   ```

2. **Obtener Movimientos del Periodo:**
   ```python
   movs = MovimientoAlmacen.objects.filter(
       empresa=empresa,
       almacen=almacen,
       producto=producto,
       fecha_documento__range=[fecha_inicio, fecha_fin],
       estado_erp__in=['V', 'F']  # Válidos y Facturados
   )
   ```

3. **Obtener Notas Externas:**
   ```python
   notas = MovimientoAlmacenNota.objects.filter(
       empresa=empresa,
       id_erp_cab__in=[m.id_erp_cab for m in movs]
   )
   ```

4. **Construir Descripción Inteligente:**
   - TD (Transferencia): "TRANSFERENCIA ENTRE ALMACENES - {almacen_ref}"
   - FT (Flete): "INGRESO POR FLETE - {glosa}"
   - Otros: "{Entidad} - {Glosa}"

5. **Calcular Saldos Acumulados:**
   ```python
   saldo = saldo_inicial
   for mov in movs_ordenados:
       saldo += (mov.entrada - mov.salida)
       mov['saldo'] = saldo
   ```

6. **Devolver JSON/Excel/PDF según formato solicitado**

### 6.5 Exportación a Excel

Usa `openpyxl` para generar archivos Excel con formato profesional:

```python
def generate_kardex_excel(data, f_inicio, f_fin, nombre_empresa):
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Estilos
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_fill = PatternFill(start_color="005f73", fill_type="solid")
    
    # Encabezado
    ws.merge_cells('A1:F1')
    ws['A1'] = f"{nombre_empresa} - REPORTE DE KARDEX ({f_inicio} al {f_fin})"
    ws['A1'].font = header_font
    ws['A1'].fill = header_fill
    
    # Por cada producto
    for producto in data.values():
        # Título producto
        ws.append([f"{producto['codigo']} - {producto['nombre']}"])
        
        # Cabeceras tabla
        ws.append(["Fecha", "Documento", "Detalle", "Entrada", "Salida", "Saldo"])
        
        # Movimientos
        for mov in producto['kardex']:
            ws.append([
                mov['fecha'],
                mov['doc'],
                mov['detalle'],
                mov['entrada'],
                mov['salida'],
                mov['saldo']
            ])
    
    # Guardar
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="kardex_{f_inicio}_{f_fin}.xlsx"'
    return response
```

---

## 7. Servicios y Utilidades

### 7.1 Servicios (almacen/services.py)

#### `get_stock_actual_rápido(empresa_id, almacen_id, producto_id)`

Consulta rápida a la tabla Stock.

```python
try:
    stock = Stock.objects.get(empresa_id=..., almacen_id=..., producto_id=...)
    return {
        'cantidad_actual': stock.cantidad_actual,
        'cantidad_en_transito': stock.cantidad_en_transito,
        'fecha_ultimo_movimiento': stock.fecha_ultimo_movimiento
    }
except Stock.DoesNotExist:
    return {'cantidad_actual': 0, 'cantidad_en_transito': 0}
```

#### `get_kardex_detallado(empresa_id, almacen_id, producto_ids, fecha_inicio, fecha_fin)`

Genera reporte Kardex completo con saldos acumulados.

**Acepta múltiples productos** para generar reportes consolidados.

### 7.2 Utilidades (almacen/utils.py)

#### `generate_kardex_excel(data, f_inicio, f_fin, nombre_empresa)`

Exporta Kardex a Excel con formato profesional.

#### `generate_kardex_pdf(data, context, nombre_empresa)`

Exporta Kardex a PDF usando WeasyPrint.

---

## 8. Sistema de Filtros

### 8.1 MovimientoAlmacenFilter

**Filtros Exactos:**
- `empresa`, `almacen`, `producto`, `producto__in`
- `tipo_documento_erp`, `tipo_documento_erp__in`
- `es_ingreso`, `proveedor_erp_id`, `cliente_erp_id`

**Filtros de Texto (icontains):**
- `numero_documento` → busca en `numero_documento_erp`
- `orden_compra` → busca en `numero_orden_compra`

**Filtros de Fecha:**
- `fecha_documento_desde`, `fecha_documento_hasta`
- Convierte a UTC automáticamente

**Búsqueda Global:**
- `search` → busca en: número_documento_erp, nombre_producto, numero_orden_compra, referencia_documento, cliente_erp_nombre

### 8.2 ProductoFilter

**Filtros:**
- `nombre_producto` (icontains)
- `codigo_producto` (icontains)
- `proveedor_marca` (icontains)
- `empresa` (exact)

### 8.3 StockFilter

**Filtros:**
- `empresa`, `almacen`, `producto` (exact)
- `search` → busca en código o nombre de producto
- `solo_con_stock` → filtra `cantidad_actual > 0`

---

## 9. Reportes y Exportaciones

### 9.1 Formatos Soportados

| Formato | Extensión | Uso |
|---------|-----------|-----|
| JSON | `.json` | API, desarrollo, debugging |
| Excel | `.xlsx` | Análisis en Excel, contabilidad |
| PDF | `.pdf` | Impresión, archivo físico |

### 9.2 Ejemplo Completo de Uso

**1. Obtener Kardex en JSON:**
```bash
GET /api/almacen/reporte-kardex/?empresa_id=1&almacen_id=2&producto_id=123&fecha_inicio=2024-01-01&fecha_fin=2024-12-31
```

**2. Descargar Excel:**
```bash
GET /api/almacen/reporte-kardex/?empresa_id=1&almacen_id=2&producto_id=123&fecha_inicio=2024-01-01&fecha_fin=2024-12-31&export_format=excel
```

**3. Descargar PDF:**
```bash
GET /api/almacen/reporte-kardex/?empresa_id=1&almacen_id=2&producto_id=123&fecha_inicio=2024-01-01&fecha_fin=2024-12-31&export_format=pdf
```

**4. Múltiples Productos (Excel):**
```bash
GET /api/almacen/reporte-kardex/?empresa_id=1&almacen_id=2&producto_id=123&producto_id=124&producto_id=125&fecha_inicio=2024-01-01&fecha_fin=2024-12-31&export_format=excel
```

---

## 10. WebSockets y Notificaciones

### 10.1 Configuración de Channels

**settings.py:**
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("127.0.0.1", 6379)]},
    },
}
ASGI_APPLICATION = 'semilla360.asgi.application'
```

### 10.2 Consumer de Sincronización

**almacen/consumers.py:**
```python
class SyncMovimientosConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.empresa_id = self.scope['url_route']['kwargs']['empresa_id']
        self.room_group_name = f"sync_movimientos_empresa_{self.empresa_id}"
        
        # Unirse al grupo
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
    
    async def sync_update(self, event):
        # Enviar mensaje al cliente
        await self.send(text_data=json.dumps({
            'status': event['status'],
            'message': event['message'],
            'result': event.get('result')
        }))
```

### 10.3 Routing

**almacen/routing.py:**
```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/sync-movimientos/(?P<empresa_id>\w+)/$', consumers.SyncMovimientosConsumer.as_asgi()),
]
```

### 10.4 Uso desde Frontend

**JavaScript:**
```javascript
const empresaId = 1;
const socket = new WebSocket(
    `ws://localhost:8000/ws/sync-movimientos/${empresaId}/`
);

socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    console.log('Status:', data.status);
    console.log('Message:', data.message);
    
    if (data.status === 'completed') {
        console.log('Resultado:', data.result);
        // Actualizar UI
    }
};

socket.onopen = function(e) {
    console.log('Conectado al WebSocket');
};

socket.onclose = function(e) {
    console.log('Desconectado del WebSocket');
};
```

---

## 11. Casos de Uso Detallados

### 11.1 Caso: Importación de Semillas

**Contexto:** Una importación de 50,000 KG de semillas de maíz desde China llega al puerto de Callao.

**Flujo:**

1. **Agente Aduanero gestiona DUA:**
   - Módulo `importaciones` crea Declaracion y sube documentos

2. **ERP Starsoft registra NI (Nota de Ingreso):**
   ```sql
   -- SQL Server (ERP)
   INSERT INTO MOVALMCAB VALUES ('AD', 'NI', '0001234', '2024-11-15', ...)
   INSERT INTO MOVALMDET VALUES ('AD', 'NI', '0001234', 1, 'SEM-MAZ-001', 50000, ...)
   ```

3. **Sync detecta nuevo movimiento (15 min después):**
   ```python
   # Task automática
   LegacyMovAlmCab.objects.create(empresa=semilla, caalma='AD', ...)
   LegacyMovAlmDet.objects.create(empresa=semilla, dealma='AD', ...)
   
   MovimientoAlmacen.objects.create(
       empresa=semilla,
       almacen=almacen_arequipa,
       producto=semilla_maiz,
       cantidad=50000,
       es_ingreso=True,
       tipo_documento_erp='NI',
       numero_documento_erp='0001234',
       id_importacion='IMP-2024-001',
       ...
   )
   
   # Recalcular stock
   Stock.recalcular_stock_completo(semilla.id, almacen_arequipa.id, semilla_maiz.id)
   # Stock antes: 10000 KG
   # Stock después: 60000 KG
   ```

4. **Usuario consulta stock:**
   ```bash
   GET /api/almacen/stock/?empresa=1&almacen=2&producto=123
   ```
   ```json
   {
     "cantidad_actual": "60000.000000",
     "cantidad_en_transito": "0.000000"
   }
   ```

5. **Usuario genera Kardex:**
   ```bash
   GET /api/almacen/reporte-kardex/?empresa_id=1&almacen_id=2&producto_id=123&fecha_inicio=2024-11-01&fecha_fin=2024-11-30&export_format=excel
   ```
   **Resultado:** Archivo Excel con:
   - Saldo anterior: 10,000 KG
   - NI-0001234: +50,000 KG → Saldo: 60,000 KG

### 11.2 Caso: Transferencia Arequipa → Lima

**Contexto:** Se necesitan 5,000 KG de semillas en Lima, se trasladan desde Arequipa.

**Flujo:**

1. **ERP emite GS (Guía de Salida) en Arequipa:**
   ```sql
   -- SQL Server
   INSERT INTO MOVALMCAB VALUES ('AD', 'GS', '0005678', '2024-11-16', ...)
   INSERT INTO MOVALMDET VALUES ('AD', 'GS', '0005678', 1, 'SEM-MAZ-001', 5000, ...)
   ```
   - Campo `carfalma` = 'AL' (almacén destino)
   - Campo `cacodmov` = 'TD' (transferencia)

2. **Sync detecta GS y crea Transferencia:**
   ```python
   # Task automática
   MovimientoAlmacen.objects.create(
       almacen=almacen_arequipa,
       producto=semilla_maiz,
       cantidad=5000,
       es_ingreso=False,  # Salida
       tipo_documento_erp='GS',
       ...
   )
   
   Transferencia.objects.create(
       empresa=semilla,
       almacen_origen=almacen_arequipa,
       almacen_destino=almacen_lima,
       producto=semilla_maiz,
       cantidad_enviada=5000,
       estado='EN_TRANSITO',
       id_erp_salida_det='AD-GS-0005678-1',
       ...
   )
   
   # Recalcular stock
   Stock.recalcular_stock_completo(semilla.id, almacen_arequipa.id, semilla_maiz.id)
   # Stock Arequipa: 60000 - 5000 = 55000 KG
   # cantidad_en_transito Arequipa: +5000 KG
   ```

3. **Usuario consulta transferencias pendientes:**
   ```bash
   GET /api/almacen/transferencias/?estado=EN_TRANSITO&almacen_destino=3
   ```
   ```json
   {
     "results": [
       {
         "id": 1,
         "almacen_origen": {"codigo": "AD", "descripcion": "ALMACEN AREQUIPA"},
         "almacen_destino": {"codigo": "AL", "descripcion": "ALMACEN LIMA"},
         "producto": {"codigo_producto": "SEM-MAZ-001"},
         "cantidad_enviada": "5000.000000",
         "estado": "EN_TRANSITO",
         "fecha_envio": "2024-11-16T09:00:00Z"
       }
     ]
   }
   ```

4. **Mercancía llega a Lima (3 días después):**
   - Usuario en Lima recibe 4,980 KG (merma de 20 KG)

5. **Usuario registra recepción:**
   ```bash
   POST /api/almacen/transferencias/1/recibir/
   {
     "cantidad_recibida": 4980,
     "notas_recepcion": "Recibido con merma de 20 KG por transporte"
   }
   ```

6. **Sistema procesa recepción:**
   ```python
   transferencia.recibir_mercaderia(
       cantidad_recibida=4980,
       fecha_recepcion=timezone.now(),
       notas="Recibido con merma de 20 KG..."
   )
   
   # Crea MovimientoAlmacen de ingreso en Lima
   MovimientoAlmacen.objects.create(
       almacen=almacen_lima,
       producto=semilla_maiz,
       cantidad=4980,
       es_ingreso=True,
       tipo_documento_erp='NI',
       ...
   )
   
   # Recalcular stocks
   Stock.recalcular_stock_completo(semilla.id, almacen_lima.id, semilla_maiz.id)
   # Stock Lima: 0 + 4980 = 4980 KG
   
   Stock.recalcular_stock_completo(semilla.id, almacen_arequipa.id, semilla_maiz.id)
   # cantidad_en_transito Arequipa: -5000 KG (ahora 0)
   ```

7. **Estado final:**
   - Transferencia: estado='RECIBIDO_PARCIAL', diferencia=-20 KG
   - Stock Arequipa: 55,000 KG (física), 0 en tránsito
   - Stock Lima: 4,980 KG (física)

### 11.3 Caso: Error en Recepción → Reversión

**Contexto:** Se recibió por error, se debe revertir.

1. **Usuario revierte:**
   ```bash
   POST /api/almacen/transferencias/1/revertir_recepcion/
   ```

2. **Sistema revierte:**
   ```python
   transferencia.revertir_recepcion()
   
   # Elimina MovimientoAlmacen de ingreso en Lima
   MovimientoAlmacen.objects.filter(
       id_erp_det='WEB-TR-1-IN'
   ).delete()
   
   # Recalcular stocks
   # Stock Lima: vuelve a 0 KG
   # cantidad_en_transito Arequipa: vuelve a 5000 KG
   ```

3. **Usuario puede volver a recibir correctamente**

---

## 12. Troubleshooting

### 12.1 Problemas Comunes

#### **Problema: Sincronización no se ejecuta**

**Síntomas:**
- Movimientos nuevos del ERP no aparecen en `/api/almacen/movimientos/`

**Solución:**
```bash
# 1. Verificar que RQ Worker esté corriendo
ps aux | grep rq

# 2. Si no está corriendo, iniciar:
python manage.py rqworker default

# 3. Verificar logs
tail -f logs/rq_tasks.log

# 4. Ejecutar sync manual
curl -X POST http://localhost:8000/api/almacen/trigger-sync/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"empresa_alias": "bd_semilla_starsoft", "days": 30}'
```

#### **Problema: Stock descuadrado**

**Síntomas:**
- Stock en `/api/almacen/stock/` no coincide con suma manual de movimientos

**Solución:**
```bash
# Recalcular stock manualmente vía shell
python manage.py shell

>>> from almacen.models import Stock, Empresa, Almacen, Producto
>>> Stock.recalcular_stock_completo(
...     empresa_id=1,
...     almacen_id=2,
...     producto_id=123
... )

# O recalcular TODO el stock de una empresa
>>> from importaciones.models import Producto
>>> from almacen.models import Almacen, Stock
>>> empresa = Empresa.objects.get(id=1)
>>> for almacen in Almacen.objects.filter(empresa=empresa):
...     for producto in Producto.objects.filter(empresa=empresa):
...         Stock.recalcular_stock_completo(empresa.id, almacen.id, producto.id)
```

#### **Problema: Transferencia atascada en EN_TRANSITO**

**Síntomas:**
- Transferencia sigue EN_TRANSITO a pesar de que hay NI en el ERP

**Causas posibles:**
- Campo `referencia_documento` de la NI no coincide con `id_erp_salida_cab` de la GS
- NI fue registrada antes de la GS (sync las procesó en orden inverso)

**Solución:**
```bash
# Recibir manualmente desde endpoint
curl -X POST http://localhost:8000/api/almacen/transferencias/1/recibir/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"cantidad_recibida": 5000, "notas_recepcion": "Recepción manual"}'

# O desde shell
>>> from almacen.models import Transferencia
>>> t = Transferencia.objects.get(id=1)
>>> t.recibir_mercaderia(5000, timezone.now(), "Recepción manual")
```

#### **Problema: Kardex lento o timeout**

**Síntomas:**
- `/api/almacen/reporte-kardex/` tarda >30 segundos o da timeout

**Causas:**
- Rango de fechas muy amplio
- Producto con miles de movimientos
- Falta índice en `fecha_documento`

**Solución:**
```bash
# 1. Reducir rango de fechas (ej: mensual en vez de anual)
GET /api/almacen/reporte-kardex/?fecha_inicio=2024-11-01&fecha_fin=2024-11-30

# 2. Verificar índices en BD
python manage.py dbshell
> SHOW INDEX FROM movimiento_almacen;

# 3. Si falta, crear índice
> CREATE INDEX idx_mov_fecha_doc ON movimiento_almacen(empresa_id, almacen_id, producto_id, fecha_documento);

# 4. Exportar a Excel en vez de JSON (más eficiente para grandes volúmenes)
GET /api/almacen/reporte-kardex/?...&export_format=excel
```

#### **Problema: WebSocket no conecta**

**Síntomas:**
- `socket.onopen` nunca se dispara
- Notificaciones de sync no llegan

**Solución:**
```bash
# 1. Verificar que Redis esté corriendo
redis-cli ping
# Debe responder: PONG

# 2. Si no, iniciar Redis
sudo service redis-server start

# 3. Verificar configuración de CHANNEL_LAYERS en settings.py
# 4. Verificar que Daphne esté corriendo (en vez de runserver)
daphne -b 0.0.0.0 -p 8000 semilla360.asgi:application

# 5. En desarrollo, usar runserver con channels
python manage.py runserver --noreload
```

### 12.2 Debugging Avanzado

#### **Habilitar Logs Detallados**

**settings.py:**
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',  # Cambiar a DEBUG
            'class': 'logging.StreamHandler',
        },
        'file_app': {
            'level': 'DEBUG',  # Cambiar a DEBUG
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/app.log',
        },
    },
    'loggers': {
        'almacen': {
            'handlers': ['console', 'file_app'],
            'level': 'DEBUG',  # Cambiar a DEBUG
            'propagate': False,
        },
    }
}
```

#### **Inspeccionar Jobs de RQ**

```python
import django_rq
queue = django_rq.get_queue('default')

# Listar todos los jobs
for job_id in queue.get_job_ids():
    job = queue.fetch_job(job_id)
    print(f"Job {job_id}: {job.func_name} - Status: {job.get_status()}")

# Ver detalles de un job específico
job = queue.fetch_job('job-id-aqui')
print(job.meta)  # Progreso
print(job.exc_info)  # Errores
```

---

## 13. Resumen de Comandos Útiles

```bash
# Iniciar RQ Worker
python manage.py rqworker default

# Iniciar Daphne (WebSockets)
daphne -b 0.0.0.0 -p 8000 semilla360.asgi:application

# Recalcular TODO el stock
python manage.py shell
>>> from almacen.tasks import recalcular_todos_los_stocks
>>> recalcular_todos_los_stocks()

# Ver logs en tiempo real
tail -f logs/app.log
tail -f logs/rq_tasks.log

# Disparar sync manual
curl -X POST http://localhost:8000/api/almacen/trigger-sync/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"empresa_alias": "bd_semilla_starsoft", "days": 30}'

# Verificar estado de sync
curl http://localhost:8000/api/almacen/check-sync-status/ \
  -H "Authorization: Bearer <token>"

# Descargar Kardex Excel
curl "http://localhost:8000/api/almacen/reporte-kardex/?empresa_id=1&almacen_id=2&producto_id=123&fecha_inicio=2024-01-01&fecha_fin=2024-12-31&export_format=excel" \
  -H "Authorization: Bearer <token>" \
  -o kardex.xlsx
```

---

## Conclusión

El módulo **Almacén** es el corazón operativo de Semilla360, proporcionando:

✅ **Sincronización Automática** con el ERP Starsoft  
✅ **Gestión de Stock** en tiempo real  
✅ **Transferencias** entre almacenes con trazabilidad completa  
✅ **Reportes Kardex** detallados en múltiples formatos  
✅ **API RESTful** con filtros avanzados y paginación  
✅ **WebSockets** para notificaciones en tiempo real  
✅ **Auditoría Completa** con soft-delete y django-simple-history  

Con **3,300+ líneas de código** optimizado y **15+ endpoints** robustos, el módulo es capaz de manejar operaciones a escala empresarial con performance y confiabilidad.

**Próximos Pasos Recomendados:**
1. Implementar dashboard de KPIs
2. Alertas automáticas por stock bajo
3. Optimización de queries con Elasticsearch
4. Mobile app para recepción de transferencias
5. Integración con sistema de facturación

---

**Documentación creada por:** GitHub Copilot  
**Fecha:** Diciembre 2024  
**Versión del Módulo:** 1.0  
**Repositorio:** github.com/EcrDevelopment/backend_semilla360
