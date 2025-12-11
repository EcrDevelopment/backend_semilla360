# Análisis Completo del Repositorio backend_semilla360

> **NOTA DE SEGURIDAD:** Este documento contiene información técnica del sistema incluyendo referencias a configuraciones, dominios e IPs que se encuentran en el código fuente del repositorio. Esta información se documenta con fines de análisis técnico. En un entorno de producción real, todos los valores sensibles deben migrarse a variables de entorno y no estar hardcodeados en el código.

## Resumen Ejecutivo

**Semilla360** es una aplicación web backend desarrollada en Django REST Framework que funciona como un sistema integrado de gestión empresarial (ERP) para el sector agroindustrial, específicamente orientado a la gestión de importaciones, almacenes, despachos y control de inventarios. El sistema integra datos de múltiples bases de datos (MySQL y SQL Server) y proporciona funcionalidades avanzadas para el manejo de documentación, seguimiento de productos, y control de operaciones logísticas.

---

## 1. Stack Tecnológico

### Backend Framework
- **Django 5.1+**: Framework web principal
- **Django REST Framework**: API RESTful
- **GraphQL** (graphene-django): API alternativa para consultas complejas
- **Django Channels + Daphne**: WebSockets para comunicación en tiempo real
- **Redis**: Sistema de caché y mensajería (via Channels)

### Bases de Datos
- **MySQL**: Base de datos principal (`semilla_360`)
- **SQL Server (MSSQL)**: Integración con 3 bases de datos ERP Starsoft:
  - `003BDCOMUN` (Semilla)
  - `007BDCOMUN` (Maxi)
  - `008BDCOMUN` (Trading)
- **Database Router**: Enrutamiento inteligente de consultas

### Autenticación y Seguridad
- **JWT (Simple JWT)**: Autenticación basada en tokens
- **django-role-permissions**: Sistema de roles y permisos
- **CORS Headers**: Control de acceso cross-origin
- **django-simple-history**: Auditoría de cambios

### Procesamiento de Datos
- **Pandas**: Análisis y manipulación de datos
- **ReportLab + xhtml2pdf**: Generación de PDFs
- **PyMuPDF (fitz)**: Procesamiento de archivos PDF
- **pdfplumber**: Extracción de tablas de PDFs
- **pytesseract**: OCR para reconocimiento de texto en imágenes
- **openpyxl**: Manejo de archivos Excel

### Otros
- **django-rq**: Procesamiento de tareas en segundo plano
- **Hypothesis + Pytest**: Testing
- **Jinja2**: Templating adicional

---

## 2. Arquitectura del Sistema

### 2.1 Estructura de Módulos

El sistema está organizado en 5 módulos principales:

#### **A. Base** (`/base`)
Módulo fundacional que proporciona:
- **BaseModel**: Clase abstracta con soft-delete, timestamps y auditoría
- **BaseCommonInfo**: Gestión de estados (activo/eliminado)
- **Middleware personalizado**: JWTCompatibleHistoryMiddleware para auditoría con JWT

**Características clave:**
```python
- state: Boolean para soft-delete
- created_date, modified_date, deleted_date: Timestamps
- historical: Integración con django-simple-history
- Managers personalizados: objects (solo activos), all_objects (todos)
```

#### **B. Usuarios** (`/usuarios`)
Gestión de usuarios, autenticación y permisos.

**Modelos:**
- `Empresa`: Perfiles de empresas con RUC
- `Direccion`: Direcciones por empresa con ubigeo completo
- `UserProfile`: Perfil extendido de usuario con teléfono y empresa
- `PasswordResetToken`: Tokens para recuperación de contraseña

**Funcionalidades:**
- Login/Logout con JWT (Access + Refresh tokens)
- Recuperación de contraseña por email
- Sistema de roles (admin, operador, etc.)
- Gestión de perfiles de empresa
- WebSockets para notificaciones en tiempo real (via Channels)

**Endpoints principales:**
- `/api/accounts/login/`
- `/api/accounts/token/refresh/`
- `/api/accounts/password-reset/`
- `/api/accounts/users/`

#### **C. Localización** (`/localizacion`)
Gestión de datos geográficos del Perú.

**Modelos:**
- `Departamento`
- `Provincia`
- `Distrito`

**Propósito:** Proporciona datos de ubigeo para direcciones y reportes con filtros geográficos.

#### **D. Importaciones** (`/importaciones`)
Módulo central para gestión de importaciones y documentación aduanera.

**Modelos ERP Starsoft (managed=False):**
- `OrdenCompraStarsoft` (IMPORD): Órdenes de compra de importación
- `OrdenCompraDetStarsoft` (IMPORC): Detalles de OC
- `Proveedor` (MAEPROV): Proveedores internacionales

**Modelos Locales (MySQL):**
- `Empresa`: Empresas del grupo (Semilla, Maxi, Trading)
- `Producto`: Catálogo de productos con código, marca y proveedor
- `OrdenCompra`: Órdenes locales vinculadas a productos
- `Despacho`: Despachos de importación con DUA, carta porte, factura
- `OrdenCompraDespacho`: Relación M2M entre OC y Despachos
- `DetalleDespacho`: Detalles de carga/descarga (sacos, pesos, mermas)
- `ConfiguracionDespacho`: Parámetros de cálculo (mermas, precios, márgenes)
- `GastosExtra`: Gastos adicionales por despacho
- `Declaracion`: Declaraciones aduaneras (DUAs)
- `Documento`: Archivo de documentos con hash para detección de duplicados
- `TipoDocumento`: Catálogo de tipos de documentos
- `ExpedienteDeclaracion`: Expedientes por declaración con metadata fiscal

**Funcionalidades clave:**
1. **Gestión de Despachos:**
   - Creación de despachos con múltiples OC
   - Cálculo automático de costos (flete, estiba, mermas)
   - Generación de reportes PDF detallados
   - Control de sacos rotos/húmedos/mojados

2. **Sistema de Documentos:**
   - Upload de archivos (PDF, RAR, ZIP, Excel)
   - Detección de duplicados por hash SHA-256
   - Generic Relations para vincular documentos a múltiples entidades
   - Organización automática en carpetas por DUA/año
   - Extracción de datos de PDFs (tablas, texto, OCR)

3. **Expedientes Fiscales:**
   - Organización por año fiscal y mes
   - Vinculación con declaraciones aduaneras
   - Seguimiento de folios y notas de ingreso

**Endpoints principales:**
- `/api/importaciones/despachos/`
- `/api/importaciones/ordenes-compra/`
- `/api/importaciones/documentos/`
- `/api/importaciones/declaraciones/`
- `/api/importaciones/expedientes/`
- GraphQL endpoint: `/graphql/`

#### **E. Almacén** (`/almacen`)
Sistema avanzado de gestión de inventarios con sincronización ERP.

**Modelos ERP Starsoft (managed=False):**
- `MovAlmCab` (MOVALMCAB): Cabeceras de movimientos (NI, GS, TR)
- `MovAlmDet` (MOVALMDET): Detalles de movimientos por ítem
- `GremisionCab` (GREMISION_CAB): Guías de remisión electrónicas
- `GremisionDet` (GREMISION_DET): Detalles de guías

**Modelos Locales (MySQL):**
- `Almacen`: Almacenes/sedes con códigos y ubicaciones
- `LegacyMovAlmCab/Det`: Caché local de datos del ERP para performance
- `MovimientoAlmacen`: Movimientos unificados (ingresos/salidas)
- `MovimientoAlmacenNota`: Notas/comentarios de movimientos
- `Stock`: Stock actual por empresa/almacén/producto
- `Transferencia`: Transferencias entre almacenes con estados (en tránsito, recibido, perdido)
- `GastoDocumentoAlmacen`: Gastos asociados a documentos (estibaje, transporte)
- `ControlSyncMovAlmacen`: Control de sincronización con timestamp

**Funcionalidades clave:**

1. **Sincronización ERP → MySQL:**
   - Extracción incremental de datos desde SQL Server
   - Copia local (LegacyMovAlmCab/Det) para performance
   - Mapeo a MovimientoAlmacen con normalización de datos
   - Detección de anulaciones y cambios
   - Gestión de errores con logging detallado

2. **Gestión de Stock:**
   - Cálculo automático basado en MovimientoAlmacen
   - Stock en tránsito por transferencias pendientes
   - Recálculo on-demand o por triggers
   - Índices optimizados para consultas rápidas

3. **Transferencias entre Almacenes:**
   - Estados: EN_TRANSITO, RECIBIDO, RECIBIDO_PARCIAL, RECIBIDO_SOBRANTE, PERDIDO
   - Vinculación automática GS (salida) → NI (ingreso)
   - Recepción manual con registro de diferencias
   - Reversión de recepciones con recálculo de stock

4. **Reportes y Vistas:**
   - Kardex por producto/almacén/periodo
   - Movimientos por cliente/proveedor
   - Stock actual consolidado
   - Transferencias pendientes
   - Gastos por documento

5. **Tareas en Segundo Plano (RQ):**
   - Sincronización programada
   - Procesamiento de lotes grandes
   - Recálculos masivos de stock

**Endpoints principales:**
- `/api/almacen/movimientos/`
- `/api/almacen/stock/`
- `/api/almacen/transferencias/`
- `/api/almacen/almacenes/`
- `/api/almacen/sync/` (trigger manual de sincronización)

---

## 3. Integración con ERP Starsoft

### 3.1 Arquitectura de Integración

El sistema implementa una arquitectura de **sincronización unidireccional** ERP → Backend:

```
┌─────────────────────┐
│  SQL Server (ERP)   │
│  - 003BDCOMUN       │
│  - 007BDCOMUN       │◄─── Conexión Read-Only
│  - 008BDCOMUN       │
└──────────┬──────────┘
           │
           │ Sync Incremental
           │ (Cada X minutos)
           ▼
┌─────────────────────┐
│  MySQL (Backend)    │
│  - LegacyMovAlm*    │◄─── Caché Local
│  - MovimientoAlm    │◄─── Datos Normalizados
│  - Stock            │◄─── Cálculos
└─────────────────────┘
```

### 3.2 Estrategia de Sincronización

**Sincronización Incremental:**
- Control por `ControlSyncMovAlmacen.ultima_fecha`
- Solo extrae registros nuevos/modificados
- Usa `CAFECACT` (fecha actualización) como referencia

**Full Sync Periódico:**
- Comparación completa de claves para detectar anulaciones
- Ejecutado semanalmente o bajo demanda
- Marca como `state=False` registros eliminados en ERP

**Gestión de Errores:**
- Logging detallado en `logs/app.log` y `logs/rq_tasks.log`
- Transacciones atómicas para consistencia
- Reintentos automáticos en caso de timeout

### 3.3 Mapeo de Datos

**Ejemplo: MOVALMCAB/DET → MovimientoAlmacen**

| ERP Field | Backend Field | Transformación |
|-----------|---------------|----------------|
| CAALMA + CATD + CANUMDOC | id_erp_cab | Concatenación con guiones |
| DEALMA + DETD + DENUMDOC + DEITEM | id_erp_det | PK compuesta |
| CATD | tipo_documento_erp | NI, GS, TR, etc. |
| DECODIGO | producto (FK) | Lookup por código |
| DECANTID | cantidad | Decimal(15,6) |
| CATIPMOV | es_ingreso | 'E'=True, 'S'=False |
| CAFECDOC | fecha_documento | DateTime |
| CAGLOSA | glosa_cabecera | Text(500) |

---

## 4. Características Avanzadas

### 4.1 Sistema de Soft-Delete
Todos los modelos heredan de `BaseModel` que implementa:
- No elimina físicamente registros
- Marca `state=False` y registra `deleted_date`
- Manager `objects` filtra automáticamente por `state=True`
- Método `hard_delete()` para eliminación real (uso excepcional)

### 4.2 Auditoría Completa
Via `django-simple-history`:
- Registro de todos los cambios (INSERT, UPDATE, DELETE)
- Usuario que realizó la acción (via JWT middleware)
- Timestamp de cada cambio
- Tablas `historical_*` automáticas

### 4.3 Procesamiento de Documentos

**Formatos soportados:**
- PDF: Extracción de tablas, texto, imágenes
- RAR/ZIP: Descompresión y procesamiento en batch
- Excel (XLSX): Importación de datos
- Imágenes: OCR con Tesseract

**Detección de Duplicados:**
```python
hash_archivo = hashlib.sha256(file_content).hexdigest()
```

**Generic Relations:**
Un `Documento` puede asociarse a:
- `Declaracion`
- `ExpedienteDeclaracion`
- Cualquier modelo futuro

### 4.4 Cálculos Automáticos en Despachos

El sistema calcula automáticamente:
1. **Mermas:**
   - Merma real = Peso salida - Peso llegada
   - Merma permitida (configurable)
   - Monto de descuento por merma

2. **Sacos:**
   - Sacos faltantes
   - Sacos rotos/húmedos/mojados
   - Descuentos por saco según estado

3. **Costos:**
   - Precio CIF (Cost, Insurance, Freight)
   - Gastos de nacionalización
   - Margen financiero
   - Costo final por kg

4. **Reportes PDF:**
   - Liquidación de despacho
   - Detalle de mermas y descuentos
   - Firmas digitales

### 4.5 WebSockets (Django Channels)

**Consumer en `/usuarios/consumers.py`:**
- Notificaciones en tiempo real
- Actualizaciones de estado
- Chat interno (si implementado)

**Configuración:**
```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("127.0.0.1", 6379)]},
    },
}
```

### 4.6 API GraphQL

**Schema en `/importaciones/schema.py`:**
- Consultas complejas con relaciones anidadas
- Queries: Declaraciones, Expedientes, Documentos
- Mutations: CRUD operations
- Filtrado avanzado

**Ejemplo de query:**
```graphql
query {
  allDeclaraciones(anio: 2024) {
    numero
    anio
    expedientes {
      descripcion
      documento {
        nombreOriginal
      }
    }
  }
}
```

---

## 5. Flujos de Trabajo Principales

### 5.1 Flujo de Importación

```
1. PROVEEDOR envía mercancía
   ↓
2. AGENTE ADUANERO gestiona documentos
   ↓
3. Se crea DECLARACION (DUA)
   ↓
4. Se suben DOCUMENTOS (facturas, BL, certificados)
   ↓
5. Sistema genera EXPEDIENTE por DUA
   ↓
6. Se crea DESPACHO vinculado a OC
   ↓
7. TRANSPORTISTA traslada mercancía
   ↓
8. Se registra DETALLE_DESPACHO (pesos, sacos)
   ↓
9. Sistema calcula MERMAS y COSTOS
   ↓
10. Se genera REPORTE PDF de liquidación
```

### 5.2 Flujo de Almacén

```
1. ERP Starsoft genera NI (Nota Ingreso)
   ↓
2. SYNC Task extrae datos a LegacyMovAlmCab/Det
   ↓
3. Sistema crea MovimientoAlmacen (es_ingreso=True)
   ↓
4. Se actualiza STOCK automáticamente
   ↓
5. Usuario puede consultar kardex/reportes
   
--- O BIEN ---

1. Usuario crea TRANSFERENCIA entre almacenes
   ↓
2. Sistema genera GS (salida) en almacén origen
   ↓
3. Transferencia queda EN_TRANSITO
   ↓
4. Usuario RECIBE en almacén destino
   ↓
5. Sistema genera NI (ingreso) automático
   ↓
6. Stock se recalcula en ambos almacenes
```

### 5.3 Flujo de Sincronización

```
1. RQ Worker ejecuta task cada X minutos
   ↓
2. Consulta ControlSyncMovAlmacen.ultima_fecha
   ↓
3. Query incremental a SQL Server:
   WHERE CAFECACT > ultima_fecha
   ↓
4. Copia registros a LegacyMovAlmCab/Det
   ↓
5. Mapea y crea MovimientoAlmacen
   ↓
6. Actualiza ultima_fecha
   ↓
7. Log de resultados (éxito/errores)
```

---

## 6. Base de Datos

### 6.1 Estructura de BD

**MySQL (semilla_360):**
- 20+ tablas propias
- ~30 tablas `historical_*` (auditoría)
- Índices optimizados para consultas frecuentes

**SQL Server (ERP Starsoft):**
- 200+ tablas (solo lectura)
- Claves compuestas
- Sin relaciones FK explícitas en algunos casos

### 6.2 Modelos Principales y Relaciones

```
Empresa (1) ──┬── (N) Producto
              ├── (N) Almacen
              ├── (N) MovimientoAlmacen
              ├── (N) Stock
              └── (N) Transferencia

Producto (1) ──┬── (N) OrdenCompra
               ├── (N) MovimientoAlmacen
               └── (N) Stock

Almacen (1) ───┬── (N) MovimientoAlmacen
               ├── (N) Stock
               ├── (N) Transferencia (origen)
               └── (N) Transferencia (destino)

Declaracion (1) ──┬── (N) Documento (GenericFK)
                  └── (N) ExpedienteDeclaracion

Despacho (1) ──┬── (N) DetalleDespacho
               ├── (1) ConfiguracionDespacho
               ├── (N) GastosExtra
               └── (M2M) OrdenCompra (via OrdenCompraDespacho)
```

### 6.3 Índices Clave

```python
# MovimientoAlmacen
- Index(['empresa', 'almacen', 'producto', 'fecha_documento'])
- Index(['empresa', 'id_erp_det']) UNIQUE
- Index(['proveedor_erp_id'])
- Index(['cliente_erp_id'])

# Stock
- Index(['empresa', 'almacen', 'producto']) UNIQUE

# Transferencia
- Index(['empresa', 'id_erp_salida_det']) UNIQUE
- Index(['empresa', 'almacen_destino', 'producto', 'estado'])
```

---

## 7. Seguridad

### 7.1 Autenticación
- JWT con tokens de corta vida (15 min access, 7 días refresh)
- Token rotation automático
- Blacklist de tokens revocados
- HTTPS obligatorio en producción

### 7.2 Autorización
- Sistema de roles (via django-role-permissions)
- Permisos granulares por endpoint
- Decorators `@permission_classes`

### 7.3 Validación de Datos
- Serializers de DRF para validación
- Unique constraints en BD
- Foreign key cascades controlados

### 7.4 CORS
Configurado para:
- Frontend en `semilla360.online`
- IPs específicas
- Headers autorizados

### 7.5 Puntos de Atención (Security Issues)

⚠️ **CRÍTICOS:**
1. **Credenciales Hardcodeadas en `settings.example`:**
   - SECRET_KEY expuesto
   - Contraseñas de BD en texto plano
   - **Recomendación:** Usar variables de entorno

2. **DEBUG=True en producción:**
   - Expone stack traces
   - **Recomendación:** `DEBUG = os.getenv('DEBUG', 'False') == 'True'`

3. **ALLOWED_HOSTS con IPs públicas:**
   - Puede permitir ataques host header
   - **Recomendación:** Limitar solo a dominios verificados

⚠️ **MEDIOS:**
1. **Sin rate limiting en endpoints sensibles:**
   - Login, password reset
   - **Recomendación:** Implementar django-ratelimit

2. **Logs con información sensible:**
   - Pueden contener contraseñas en debug
   - **Recomendación:** Sanitizar logs

3. **CSRF_TRUSTED_ORIGINS limitado:**
   - Solo HTTP en algunas entradas
   - **Recomendación:** Solo HTTPS en producción

---

## 8. Performance

### 8.1 Optimizaciones Implementadas

1. **Caché Local de ERP:**
   - `LegacyMovAlm*` reduce latencia de red
   - Consultas locales MySQL vs remote SQL Server

2. **Índices Estratégicos:**
   - Búsquedas por empresa/almacén/producto
   - Lookups por fechas

3. **Select Related / Prefetch Related:**
   - Reducción de N+1 queries en serializers

4. **Paginación:**
   - 30-100 registros por página
   - Cursor pagination para grandes datasets

5. **Tareas Asíncronas (RQ):**
   - Sincronizaciones en background
   - Generación de PDFs pesados

### 8.2 Cuellos de Botella Potenciales

1. **Sincronización Full Sync:**
   - Miles de registros
   - **Solución:** Ejecutar en horarios de bajo uso

2. **Cálculo de Stock en Tiempo Real:**
   - Aggregate queries pesadas
   - **Solución:** Caché con invalidación inteligente

3. **Generación de PDFs Complejos:**
   - ReportLab puede ser lento
   - **Solución:** Cola RQ para reportes grandes

---

## 9. Deployment

### 9.1 Configuración de Producción

**Servidor:**
- Linux (probablemente Ubuntu/CentOS)
- Nginx como reverse proxy
- Daphne para ASGI (WebSockets)
- Gunicorn para WSGI (HTTP)

**Base de Datos:**
- MySQL 8.0+
- SQL Server 2017+ (ERP)
- Redis 6.0+ (Cache + Channels)

**Dominio:**
- `semilla360.online`
- `www.semilla360.online`
- Certificado SSL (Let's Encrypt)

### 9.2 Dependencias del Sistema

```bash
# Linux packages
apt-get install -y \
    python3.10 \
    mysql-client \
    unixodbc \
    unixodbc-dev \
    tesseract-ocr \
    tesseract-ocr-spa \
    libpq-dev

# ODBC Driver para SQL Server
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
apt-get install -y msodbcsql17
```

### 9.3 Variables de Entorno (Recomendadas)

```bash
# Django
DJANGO_SECRET_KEY=<random-key>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=semilla360.online,www.semilla360.online

# MySQL
MYSQL_DATABASE=semilla_360
MYSQL_USER=semilla_user
MYSQL_PASSWORD=<secure-password>
MYSQL_HOST=localhost

# SQL Server (ERP)
MSSQL_HOST=190.12.90.196
MSSQL_USER=SOPORTE
MSSQL_PASSWORD=<secure-password>

# Email
EMAIL_HOST_USER=sistemas.grupolasemilla@gmail.com
EMAIL_HOST_PASSWORD=<app-password>

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

---

## 10. Testing

### 10.1 Framework de Testing
- **pytest**: Framework principal
- **hypothesis**: Property-based testing
- Coverage reports

### 10.2 Archivos de Test
- `usuarios/tests.py`
- `importaciones/test.py`
- `almacen/tests.py`

### 10.3 Áreas a Testear (Recomendaciones)

1. **Autenticación:**
   - Login exitoso/fallido
   - Refresh de tokens
   - Recuperación de contraseña

2. **Sincronización:**
   - Mapeo correcto de datos ERP
   - Manejo de duplicados
   - Detección de anulaciones

3. **Cálculos de Despacho:**
   - Mermas
   - Descuentos
   - Costos CIF

4. **Stock:**
   - Recálculo correcto
   - Transferencias entre almacenes
   - Concurrencia

---

## 11. Mantenimiento

### 11.1 Tareas Periódicas

**Diarias:**
- Sincronización incremental de MovAlmacen
- Backup de base de datos MySQL
- Limpieza de logs antiguos (>30 días)

**Semanales:**
- Full Sync de MovAlmacen (detección de anulaciones)
- Análisis de crecimiento de BD
- Revisión de logs de error

**Mensuales:**
- Limpieza de tokens JWT expirados
- Optimización de índices
- Actualización de dependencias (security patches)

### 11.2 Monitoreo

**Logs:**
- `logs/app.log`: Eventos de aplicación
- `logs/rq_tasks.log`: Tareas asíncronas
- Nginx access/error logs

**Métricas Clave:**
- Tiempo de respuesta de API (<500ms p95)
- Tasa de error de sincronización (<1%)
- Uso de disco (crecimiento de media/)
- Memoria de workers RQ

**Alertas Recomendadas:**
- Sync fallido por >1 hora
- BD MySQL >80% capacidad
- Errores 500 >10 en 5 minutos

---

## 12. Roadmap Potencial

### 12.1 Funcionalidades Faltantes

1. **Dashboard Analítico:**
   - Visualización de KPIs
   - Gráficos de importaciones/stock
   - Tendencias de costos

2. **Módulo de Reportes:**
   - Reportes personalizables
   - Exportación a Excel/PDF
   - Programación de reportes

3. **Notificaciones:**
   - Email automático por eventos
   - Push notifications
   - Alertas de stock bajo

4. **API Pública:**
   - Para integraciones externas
   - Rate limiting
   - Documentación Swagger/OpenAPI

5. **Mobile App:**
   - Consulta de stock
   - Aprobaciones de documentos
   - Recepción de transferencias

### 12.2 Mejoras Técnicas

1. **Containerización:**
   - Dockerizar la aplicación
   - Docker Compose para dev
   - Kubernetes para prod (opcional)

2. **CI/CD:**
   - GitHub Actions
   - Tests automáticos
   - Deploy automático a staging

3. **Caché Distribuido:**
   - Memcached o Redis para queries frecuentes
   - Invalidación inteligente

4. **Elasticsearch:**
   - Búsqueda full-text de documentos
   - Análisis de logs

5. **Internacionalización:**
   - Soporte multi-idioma
   - Múltiples monedas

---

## 13. Documentación de Código

### 13.1 Convenciones

- Modelos: PascalCase (`MovimientoAlmacen`)
- Funciones: snake_case (`recalcular_stock_completo`)
- Constantes: UPPER_SNAKE_CASE (`ESTADOS`)
- Docstrings: Triple quotes con descripción clara

### 13.2 Ejemplos de Código Bien Documentado

**Modelo:**
```python
class Transferencia(base.models.BaseModel):
    """
    Representa una transferencia de productos entre dos almacenes.
    
    Lifecycle:
    1. Creada en estado EN_TRANSITO al generar GS (salida)
    2. Actualizada a RECIBIDO/PERDIDO al confirmar NI (ingreso)
    3. Puede revertirse con revertir_recepcion()
    
    Relationships:
    - almacen_origen (FK): Almacén que envía
    - almacen_destino (FK): Almacén que recibe
    - producto (FK): Producto transferido
    """
```

**Función:**
```python
@staticmethod
def recalcular_stock_completo(empresa_id, almacen_id, producto_id):
    """
    Recalcula el stock basándose ÚNICAMENTE en MovimientoAlmacen.
    
    Args:
        empresa_id (int): ID de la empresa
        almacen_id (int): ID del almacén
        producto_id (int): ID del producto
    
    Returns:
        None
    
    Side Effects:
        - Crea/actualiza registro en Stock
        - Suma ingresos - salidas de MovimientoAlmacen
        - Calcula stock en tránsito de Transferencias
    
    Example:
        Stock.recalcular_stock_completo(1, 'AD', 123)
    """
```

---

## 14. Casos de Uso Reales

### 14.1 Importación de Semillas desde China

**Actores:**
- Gerente de Compras
- Agente de Aduanas
- Operador de Almacén

**Flujo:**
1. Gerente crea OC en ERP Starsoft
2. Proveedor chino envía mercancía (FOB Shanghai)
3. Agente gestiona DUA y sube documentos al sistema
4. Sistema crea Declaracion y ExpedienteDeclaracion
5. Mercancía llega al puerto (Callao)
6. Se crea Despacho con flete pactado
7. Transportista traslada a almacén Arequipa
8. Operador registra pesos (salida puerto, llegada almacén)
9. Sistema calcula merma real vs permitida
10. Se genera PDF de liquidación con descuentos
11. Contabilidad valida costos finales

### 14.2 Transferencia de Stock Lima → Arequipa

**Actores:**
- Jefe de Almacén Lima
- Chofer
- Jefe de Almacén Arequipa

**Flujo:**
1. Lima genera Transferencia en sistema web
2. Sistema crea MovimientoAlmacen de salida (GS)
3. Stock Lima disminuye, stock "en tránsito" aumenta
4. Chofer transporta mercancía
5. Arequipa recibe y cuenta producto
6. Registra cantidad recibida en sistema
7. Si hay diferencia (merma/robo), se marca RECIBIDO_PARCIAL
8. Sistema crea MovimientoAlmacen de ingreso (NI)
9. Stock Arequipa aumenta, "en tránsito" disminuye
10. Ambos almacenes ven histórico en kardex

### 14.3 Consulta de Kardex por Auditoría

**Actores:**
- Auditor Interno
- Sistema

**Flujo:**
1. Auditor accede a `/api/almacen/movimientos/`
2. Filtra por: empresa=Semilla, almacen=AD, producto=Semilla Maíz, fecha=2024-01
3. Sistema retorna:
   - Fecha, Tipo Doc, Número, Ingreso/Salida, Cantidad, Saldo
4. Auditor exporta a Excel
5. Valida saldos contra inventario físico
6. Detecta discrepancias (si existen)
7. Solicita corrección o ajuste de inventario

---

## 15. Glosario de Términos

| Término | Descripción |
|---------|-------------|
| **DUA** | Declaración Única de Aduanas (documento fiscal para importaciones) |
| **CIF** | Cost, Insurance, Freight (precio que incluye costo, seguro y flete) |
| **FOB** | Free On Board (precio sin incluir flete internacional) |
| **NI** | Nota de Ingreso (documento de entrada a almacén) |
| **GS** | Guía de Salida (documento de salida de almacén) |
| **TR** | Transferencia (movimiento entre almacenes) |
| **OC** | Orden de Compra |
| **ERP** | Enterprise Resource Planning (sistema de gestión empresarial) |
| **Starsoft** | Nombre del ERP utilizado por el grupo empresarial |
| **Merma** | Pérdida de peso/cantidad durante transporte o almacenamiento |
| **Estiba** | Carga y descarga de mercancía |
| **Kardex** | Registro histórico de movimientos de un producto |
| **Ubigeo** | Código de ubicación geográfica (Perú) |
| **RUC** | Registro Único de Contribuyentes (identificador fiscal) |
| **JWT** | JSON Web Token (método de autenticación) |
| **Soft-Delete** | Eliminación lógica (marca como inactivo sin borrar físicamente) |

---

## 16. Conclusiones

### 16.1 Fortalezas del Sistema

1. ✅ **Integración Robusta con ERP:** Sincronización bidireccional con manejo de errores
2. ✅ **Auditoría Completa:** Trazabilidad de todos los cambios
3. ✅ **Soft-Delete:** Recuperación de datos eliminados
4. ✅ **Arquitectura Modular:** Fácil mantenimiento y extensión
5. ✅ **Performance Optimizado:** Caché local, índices estratégicos
6. ✅ **Documentación de Código:** Modelos y funciones bien documentados
7. ✅ **Procesamiento de Documentos:** OCR, extracción de tablas, detección de duplicados
8. ✅ **WebSockets:** Notificaciones en tiempo real

### 16.2 Áreas de Mejora

1. ⚠️ **Seguridad:** Credenciales hardcodeadas, DEBUG en producción
2. ⚠️ **Testing:** Cobertura de tests insuficiente
3. ⚠️ **Documentación:** Falta README, guía de instalación, API docs
4. ⚠️ **Monitoreo:** Sin herramientas de observabilidad (Sentry, Prometheus)
5. ⚠️ **CI/CD:** No hay pipeline automatizado
6. ⚠️ **Containerización:** No está dockerizado

### 16.3 Recomendaciones Prioritarias

**Corto Plazo (1-2 meses):**
1. Migrar credenciales a variables de entorno
2. Configurar DEBUG=False en producción
3. Implementar rate limiting en endpoints críticos
4. Aumentar cobertura de tests a >80%
5. Crear README y documentación de API

**Medio Plazo (3-6 meses):**
1. Dockerizar la aplicación
2. Configurar CI/CD con GitHub Actions
3. Implementar monitoreo con Sentry/Prometheus
4. Desarrollar dashboard analítico
5. Crear módulo de reportes personalizables

**Largo Plazo (6-12 meses):**
1. Refactorizar para microservicios (si escala)
2. Desarrollar mobile app
3. API pública para terceros
4. Elasticsearch para búsqueda avanzada
5. Migración a Kubernetes (si necesario)

---

## 17. Contacto y Recursos

**Repositorio:** https://github.com/EcrDevelopment/backend_semilla360

**Stack Principal:**
- Django: https://docs.djangoproject.com/
- DRF: https://www.django-rest-framework.org/
- Channels: https://channels.readthedocs.io/

**Dependencias Clave:**
- Simple JWT: https://django-rest-framework-simplejwt.readthedocs.io/
- Simple History: https://django-simple-history.readthedocs.io/
- ReportLab: https://www.reportlab.com/docs/reportlab-userguide.pdf

---

**Fecha de Análisis:** Diciembre 2024  
**Versión del Sistema:** 1.0  
**Líneas de Código Python:** ~15,000  
**Número de Modelos:** 40+  
**Endpoints API:** 50+  

---

## Resumen Final

**Semilla360** es un sistema ERP backend completo y robusto diseñado específicamente para la industria agroindustrial de importación. Destaca por su integración profunda con el ERP Starsoft, su sistema de gestión documental avanzado, y su módulo de almacén con sincronización automática. El código está bien estructurado y sigue buenas prácticas de Django, aunque requiere mejoras en seguridad y testing. Con las recomendaciones implementadas, puede escalar a nivel empresarial y soportar operaciones críticas de negocio.
