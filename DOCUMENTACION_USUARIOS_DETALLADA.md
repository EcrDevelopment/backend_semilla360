# Documentación Detallada del Módulo Usuarios

## Índice
1. [Introducción y Propósito](#introducción-y-propósito)
2. [Arquitectura del Módulo](#arquitectura-del-módulo)
3. [Modelos de Datos](#modelos-de-datos)
4. [Sistema de Autenticación](#sistema-de-autenticación)
5. [Sistema de Roles y Permisos](#sistema-de-roles-y-permisos)
6. [API Endpoints](#api-endpoints)
7. [Serializers y Validaciones](#serializers-y-validaciones)
8. [WebSockets y Tiempo Real](#websockets-y-tiempo-real)
9. [Recuperación de Contraseña](#recuperación-de-contraseña)
10. [Gestión de Empresas y Direcciones](#gestión-de-empresas-y-direcciones)
11. [Casos de Uso](#casos-de-uso)
12. [Evaluación y Mejoras Propuestas](#evaluación-y-mejoras-propuestas)

---

## 1. Introducción y Propósito

### ¿Qué es el Módulo Usuarios?

El módulo **Usuarios** es el sistema central de autenticación, autorización y gestión de usuarios de Semilla360. Proporciona:

- **Autenticación JWT**: Login/logout con tokens access y refresh
- **Sistema de Roles**: Basado en django-role-permissions  
- **Permisos Granulares**: Control de acceso por funcionalidad
- **Recuperación de Contraseña**: Vía email con tokens temporales
- **Gestión de Perfiles**: Información extendida de usuarios
- **Multi-empresa**: Usuarios asociados a empresas específicas
- **WebSockets**: Notificaciones en tiempo real

### Estadísticas del Módulo

- **Líneas de Código**: ~776 líneas Python
- **Modelos**: 4 modelos propios
- **Endpoints API**: 20+ endpoints
- **Roles Definidos**: 6 roles predefinidos
- **Sistema de Permisos**: Django permissions + role-permissions

### Objetivos Clave

1. **Seguridad**: Autenticación robusta con JWT y tokens de corta vida
2. **Escalabilidad**: Sistema de roles extensible para nuevas funcionalidades
3. **Usabilidad**: Recuperación de contraseña automática vía email
4. **Multi-tenancy**: Soporte para múltiples empresas con datos aislados
5. **Auditoría**: Trazabilidad completa con django-simple-history

---

## 2. Arquitectura del Módulo

### 2.1 Diagrama de Componentes

```
┌────────────────────────────────────────────────────────────┐
│                   CAPA DE AUTENTICACIÓN                    │
│  JWT (Simple JWT) → Access Token (15 min) + Refresh (7d)  │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│                   CAPA DE AUTORIZACIÓN                     │
│  django-role-permissions → Roles → Permisos                │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│                   CAPA DE APLICACIÓN                       │
│  ViewSets → Serializers → Permissions Classes              │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│                   CAPA DE DATOS                            │
│  User (Django) → UserProfile → Empresa → Direccion         │
└────────────────────────────────────────────────────────────┘
```

### 2.2 Flujo de Autenticación

```
[Usuario] → POST /api/accounts/auth/login/ (username, password)
    ↓
[CustomTokenObtainPairView] → Valida credenciales
    ↓
[CustomTokenObtainPairSerializer] → Genera tokens JWT
    ↓
[Response] → {access, refresh, user: {...}, roles: [...], permissions: {...}}
    ↓
[Frontend] → Guarda tokens (localStorage/cookies)
    ↓
[Requests subsecuentes] → Header: Authorization: Bearer <access_token>
    ↓
[JWTAuthentication Middleware] → Valida token en cada request
```

---

## 3. Modelos de Datos

### 3.1 Empresa

Representa una empresa del grupo (Semilla, Maxi, Trading, etc.).

**Hereda de**: `BaseModel` (soft-delete, auditoría, timestamps)

**Campos**:
```python
nombre = CharField(255)           # Nombre de la empresa
direccion = TextField              # Dirección principal (opcional)
ruc = CharField(11, unique=True)  # RUC único (validación SUNAT)
```

**Métodos**:
```python
def tiene_direcciones(self):
    return self.direcciones.exists()
```

**Relaciones**:
- `direcciones` (OneToMany) → Direccion
- `empresa` (OneToMany) → UserProfile

**Tabla**: `empresa_perfil`

### 3.2 Direccion

Almacena múltiples direcciones por empresa con ubigeo completo.

**Hereda de**: `BaseModel`

**Campos**:
```python
empresa = ForeignKey(Empresa, related_name='direcciones')
direccion = TextField(2500)
departamento = ForeignKey(Departamento)  # Del módulo localizacion
provincia = ForeignKey(Provincia)
distrito = ForeignKey(Distrito)
```

**Tabla**: `direccion`

**Ejemplo de uso**:
```python
# Crear dirección para una empresa
direccion = Direccion.objects.create(
    empresa=empresa,
    direccion="Av. Los Incas 123",
    departamento=arequipa,
    provincia=arequipa,
    distrito=jose_luis_bustamante
)

# Obtener todas las direcciones de una empresa
direcciones = empresa.direcciones.filter(state=True)
```

### 3.3 UserProfile

Extiende el modelo User de Django con información adicional.

**Hereda de**: `BaseModel`

**Campos**:
```python
user = OneToOneField(User, related_name="userprofile")
telefono = CharField(20, null=True, blank=True)
empresa = ForeignKey(Empresa, related_name='empresa', null=True, blank=True)
```

**Tabla**: `perfil`

**Relación con User**:
- Creado automáticamente al crear un usuario
- Acceso: `user.userprofile.telefono`, `user.userprofile.empresa`

**Ejemplo**:
```python
# Obtener perfil del usuario autenticado
profile = request.user.userprofile
print(f"Empresa: {profile.empresa.nombre}")
print(f"Teléfono: {profile.telefono}")
```

### 3.4 PasswordResetToken

Tokens temporales para recuperación de contraseña.

**NO hereda de BaseModel** (modelo simple sin auditoría)

**Campos**:
```python
user = ForeignKey(User)
token = TextField(editable=False)     # JWT token
created_at = DateTimeField(auto_now_add=True)
active = BooleanField(default=True)
```

**Métodos**:
```python
def is_expired(self):
    """Token expira en 15 minutos"""
    return not self.active or timezone.now() > self.created_at + timedelta(minutes=15)
```

**Tabla**: `password_reset_token`

**Flujo de uso**:
1. Usuario solicita reset → Se crea token activo
2. Se envía email con link que contiene el token
3. Usuario hace clic en link → Frontend extrae token
4. Usuario ingresa nueva contraseña → Backend valida token
5. Si válido: cambia contraseña y marca token como `active=False`

---

## 4. Sistema de Autenticación

### 4.1 JWT (JSON Web Tokens)

**Configuración** (`settings.py`):
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # Token de acceso
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),      # Token de refresco
    'ROTATE_REFRESH_TOKENS': True,                    # Rota refresh en cada uso
    'BLACKLIST_AFTER_ROTATION': True,                 # Invalida refresh antiguo
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
}
```

### 4.2 CustomTokenObtainPairSerializer

Extiende el serializer estándar de Simple JWT para incluir roles y permisos.

**Campos adicionales en el token**:
```python
@classmethod
def get_token(cls, user):
    token = super().get_token(user)
    token['roles'] = [role.get_name() for role in get_user_roles(user)]
    token['permissions'] = available_perm_status(user)
    return token
```

**Respuesta de login**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@semilla360.com",
    "nombre": "Juan",
    "apellido": "Pérez",
    "profile_id": null,
    "empresa_id": 1,
    "telefono": "+51987654321"
  },
  "roles": ["SystemAdmin", "ImportacionesAdmin"],
  "permissions": {
    "importaciones": true,
    "importaciones.ver_fletes_internacionales": true,
    "importaciones.administrar_documentos_dua": true,
    ...
  }
}
```

### 4.3 Endpoints de Autenticación

#### **POST /api/accounts/auth/login/**

Autenticar usuario y obtener tokens.

**Request**:
```json
{
  "username": "admin",
  "password": "Password123!"
}
```

**Response (200 OK)**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@semilla360.com",
    "nombre": "Juan",
    "apellido": "Pérez",
    "empresa_id": 1,
    "telefono": "+51987654321"
  },
  "roles": ["SystemAdmin"],
  "permissions": {...}
}
```

**Errores**:
- `401 Unauthorized`: Credenciales inválidas

#### **POST /api/accounts/auth/token/refresh/**

Refrescar access token usando refresh token.

**Request**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK)**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",  
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."  // Nuevo refresh (rotación)
}
```

**Nota**: El sistema rota los refresh tokens. El antiguo queda en blacklist.

#### **POST /api/accounts/auth/token/verify/**

Verificar si un token es válido.

**Request**:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response**:
- `200 OK`: Token válido
- `401 Unauthorized`: Token inválido o expirado

---

## 5. Sistema de Roles y Permisos

### 5.1 Biblioteca: django-role-permissions

**Ventajas**:
- ✅ Roles predefinidos en código (no en BD)
- ✅ Permisos granulares por funcionalidad
- ✅ Fácil de extender
- ✅ Se integra con Django permissions

### 5.2 Roles Definidos (`usuarios/roles.py`)

#### **SystemAdmin**
Admin del sistema con permisos de mantenimiento.

```python
class SystemAdmin(AbstractUserRole):
    available_permissions = {
        'mantenimiento.tabla_tipo_documentos': True,
    }
```

#### **ImportacionesAdmin**
Administrador del módulo de importaciones.

```python
class ImportacionesAdmin(AbstractUserRole):
    available_permissions = {
        'importaciones': True,
        'importaciones.ver_fletes_internacionales': True,
        'importaciones.registrar_flete_internacional': True,
        'importaciones.ver_reporte_flete': True,
        'importaciones.ver_reporte_estibas': True,
        'importaciones.administrar_documentos_dua': True,
        'importaciones.administrar_expedientes_dua': True,
        'importaciones.editar_expedientes_dua': True,
        'importaciones.descargar_expedientes_dua': True,
        'importaciones.agregar_mes_expedientes_dua': True,
        'importaciones.agregar_empresa_expedientes_dua': True,
    }
```

#### **ImportacionesAsis**
Asistente de importaciones (permisos limitados).

```python
class ImportacionesAsis(AbstractUserRole):
    available_permissions = {
        'importaciones.ver_fletes_internacionales': True,
        'importaciones.administrar_documentos_dua': True,
        'importaciones.administrar_expedientes_dua': True,
        'importaciones.editar_expedientes_dua': True,
        'importaciones.descargar_expedientes_dua': True,
        'importaciones.agregar_mes_expedientes_dua': True,
        'importaciones.agregar_empresa_expedientes_dua': True,
    }
```

#### **accountsAdmin**
Administrador de usuarios.

```python
class accountsAdmin(AbstractUserRole):
    available_permissions = {
        'user.listar_usuarios': True,
        'user.registrar_usuario': True,
        'user.editar_usuario': True,
    }
```

#### **accountsUser**
Usuario estándar (puede editar su propio perfil).

```python
class accountsUser(AbstractUserRole):
    available_permissions = {
        'user.editar_perfil': True,
    }
```

#### **proveedor**
Rol para proveedores externos.

```python
class proveedor(AbstractUserRole):
    available_permissions = {
        'proveedor.cargar_documentos': True,
        'proveedor.administrar_documentos': True,
    }
```

### 5.3 Verificación de Permisos en el Código

**En vistas**:
```python
from rolepermissions.checkers import has_role, has_permission

# Verificar rol
if has_role(request.user, 'SystemAdmin'):
    # Permitir acceso

# Verificar permiso específico
if has_permission(request.user, 'importaciones.ver_fletes_internacionales'):
    # Permitir acceso
```

**Permission Class personalizada**:
```python
class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and has_role(request.user, 'accounts_admin')
```

**Uso en ViewSets**:
```python
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]
```

---

## 6. API Endpoints

### 6.1 Resumen de Endpoints

| Endpoint | Método | Descripción | Autenticación |
|----------|--------|-------------|---------------|
| `/api/accounts/auth/login/` | POST | Login y obtener tokens JWT | Ninguna |
| `/api/accounts/auth/token/refresh/` | POST | Refrescar access token | Ninguna |
| `/api/accounts/auth/token/verify/` | POST | Verificar validez de token | Ninguna |
| `/api/accounts/auth/password-reset/` | POST | Solicitar reset de contraseña | Ninguna |
| `/api/accounts/auth/password-reset-confirm/` | POST | Confirmar reset con token | Ninguna |
| `/api/accounts/usuarios` | GET, POST | CRUD usuarios | IsAuthenticated + IsAdminRole |
| `/api/accounts/usuarios/{id}` | GET, PUT, PATCH, DELETE | Detalle usuario | IsAuthenticated + IsAdminRole |
| `/api/accounts/roles` | GET, POST | CRUD roles (Groups) | IsAuthenticated + IsAdminRole |
| `/api/accounts/roles/{id}` | GET, PUT, PATCH, DELETE | Detalle rol | IsAuthenticated + IsAdminRole |
| `/api/accounts/permisos` | GET, POST | CRUD permisos | IsAuthenticated + IsAdminRole |
| `/api/accounts/empresas/` | GET, POST | Listar/crear empresas | IsAuthenticated |
| `/api/accounts/empresas/{id}/` | GET, PUT, DELETE | Detalle empresa | IsAuthenticated |
| `/api/accounts/direcciones/` | GET, POST | Listar/crear direcciones | IsAuthenticated |
| `/api/accounts/direcciones/{id}/` | GET, PUT, DELETE | Detalle dirección | IsAuthenticated |
| `/api/accounts/empresas/{id}/direcciones/` | GET | Direcciones por empresa | IsAuthenticated |
| `/api/accounts/content_types/` | GET | Content types (para permisos) | IsAuthenticated |
| `/api/accounts/departamentos/` | GET | Listar departamentos | IsAuthenticated |
| `/api/accounts/provincias/` | GET | Listar provincias | IsAuthenticated |
| `/api/accounts/distritos/` | GET | Listar distritos | IsAuthenticated |

### 6.2 Endpoints Detallados

#### **GET/POST /api/accounts/usuarios**

Listar o crear usuarios.

**Permisos**: `IsAuthenticated + IsAdminRole`

**GET Response**:
```json
[
  {
    "id": 1,
    "username": "admin",
    "email": "admin@semilla360.com",
    "first_name": "Juan",
    "last_name": "Pérez",
    "roles": [1, 2],  // IDs de Groups
    "permissions": [10, 11, 12],  // IDs de Permissions
    "userprofile": {
      "empresa_id": 1,
      "telefono": "+51987654321"
    }
  },
  ...
]
```

**POST Request** (Crear usuario):
```json
{
  "username": "nuevo_usuario",
  "password": "Password123!",
  "email": "usuario@semilla360.com",
  "first_name": "Carlos",
  "last_name": "Gómez",
  "roles": [2],  // IDs de Groups (ImportacionesAdmin)
  "permissions": [],
  "userprofile": {
    "empresa_id": 1,
    "telefono": "+51912345678"
  }
}
```

**POST Response (201 Created)**:
```json
{
  "id": 5,
  "username": "nuevo_usuario",
  "email": "usuario@semilla360.com",
  "first_name": "Carlos",
  "last_name": "Gómez",
  "roles": [2],
  "permissions": [],
  "userprofile": {
    "empresa_id": 1,
    "telefono": "+51912345678"
  }
}
```

**Validaciones**:
- ✅ Username único
- ✅ Email válido y único
- ✅ Password mínimo 8 caracteres
- ✅ Roles y permisos deben existir

#### **PUT/PATCH /api/accounts/usuarios/{id}**

Actualizar usuario.

**PUT Request** (actualización completa):
```json
{
  "username": "usuario_actualizado",
  "email": "usuario@semilla360.com",
  "first_name": "Carlos",
  "last_name": "Gómez",
  "password": "NuevaPassword123!",  // Opcional: cambiar contraseña
  "roles": [2, 3],
  "permissions": [10],
  "userprofile": {
    "empresa_id": 2,
    "telefono": "+51999888777"
  }
}
```

**PATCH Request** (actualización parcial):
```json
{
  "userprofile": {
    "telefono": "+51999888777"
  }
}
```

**Notas**:
- Si se incluye `password`, se actualiza con hash seguro
- Si no se incluye `password`, no se modifica
- Perfil se crea automáticamente si no existe

#### **POST /api/accounts/auth/password-reset/**

Solicitar restablecimiento de contraseña.

**Request**:
```json
{
  "email": "usuario@semilla360.com"
}
```

**Response (200 OK)**:
```json
{
  "message": "Correo enviado con éxito"
}
```

**Proceso interno**:
1. Valida que el email exista en la BD
2. Desactiva tokens anteriores del usuario
3. Genera nuevo JWT access token
4. Crea registro en `PasswordResetToken`
5. Envía email con plantilla HTML
6. Email contiene link: `https://semilla360.online/reset-password/confirm?token={token}&user={user_id}`

**Template del email** (`usuarios/templates/emails/password_reset.html`):
```html
<!DOCTYPE html>
<html>
<body>
  <h2>Restablecimiento de contraseña - Semilla-360°</h2>
  <p>Haz clic en el siguiente enlace para restablecer tu contraseña:</p>
  <a href="{{reset_link}}">Restablecer contraseña</a>
  <p>Este enlace expira en 15 minutos.</p>
</body>
</html>
```

#### **POST /api/accounts/auth/password-reset-confirm/**

Confirmar restablecimiento con token.

**Request**:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user_id": 5,
  "new_password": "NuevaPassword123!"
}
```

**Validaciones**:
- ✅ Token existe en BD
- ✅ Token no ha expirado (15 min)
- ✅ Token está activo (`active=True`)
- ✅ `user_id` coincide con el token
- ✅ Usuario existe
- ✅ Nueva contraseña cumple requisitos:
  - Mínimo 8 caracteres
  - Al menos 1 mayúscula
  - Al menos 1 minúscula
  - Al menos 1 número
  - Al menos 1 carácter especial

**Response (200 OK)**:
```json
{
  "message": "Contraseña restablecida con éxito."
}
```

**Proceso interno**:
1. Valida token y contraseña
2. Actualiza contraseña del usuario con hash
3. Marca token como `active=False`

---

## 7. Serializers y Validaciones

### 7.1 UserSerializer

Serializer completo para CRUD de usuarios.

**Campos anidados**:
- `roles` → `groups` (Many-to-Many con Group)
- `permissions` → `user_permissions` (Many-to-Many con Permission)
- `userprofile` → Anidado con UserProfileSerializer

**Métodos principales**:

**create()**:
```python
def create(self, validated_data):
    roles = validated_data.pop("groups", [])
    perms = validated_data.pop("user_permissions", [])
    profile_data = validated_data.pop("userprofile", {})
    password = validated_data.pop("password")
    
    user = User.objects.create_user(password=password, **validated_data)
    user.groups.set(roles)
    user.user_permissions.set(perms)
    
    UserProfile.objects.create(user=user, **profile_data)
    
    return user
```

**update()**:
```python
def update(self, instance, validated_data):
    roles = validated_data.pop("groups", None)
    perms = validated_data.pop("user_permissions", None)
    profile_data = validated_data.pop("userprofile", {})
    password = validated_data.pop("password", None)
    
    # Actualizar campos básicos
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    
    # Actualizar contraseña (con hash)
    if password:
        instance.set_password(password)
    instance.save()
    
    # Actualizar roles y permisos
    if roles is not None:
        instance.groups.set(roles)
    if perms is not None:
        instance.user_permissions.set(perms)
    
    # Actualizar o crear perfil
    profile = getattr(instance, "userprofile", None)
    if profile:
        for attr, value in profile_data.items():
            setattr(profile, attr, value)
        profile.save()
    elif profile_data:
        UserProfile.objects.create(user=instance, **profile_data)
    
    return instance
```

### 7.2 PasswordResetConfirmSerializer

Validación robusta para reset de contraseña.

**Validaciones de contraseña**:
```python
# Mínimo 8 caracteres
if len(new_password) < 8:
    raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")

# Al menos 1 mayúscula
if not re.search(r"[A-Z]", new_password):
    raise serializers.ValidationError("La contraseña debe contener al menos una letra mayúscula.")

# Al menos 1 minúscula
if not re.search(r"[a-z]", new_password):
    raise serializers.ValidationError("La contraseña debe contener al menos una letra minúscula.")

# Al menos 1 número
if not re.search(r"[0-9]", new_password):
    raise serializers.ValidationError("La contraseña debe contener al menos un número.")

# Al menos 1 carácter especial
if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
    raise serializers.ValidationError("La contraseña debe contener al menos un carácter especial.")
```

---

## 8. WebSockets y Tiempo Real

### 8.1 MainConsumer

Consumer genérico para notificaciones en tiempo real.

**Ubicación**: `usuarios/consumers.py`

**Características**:
- Autenticación JWT via query param
- Suscripción dinámica a grupos
- Manejo de notificaciones generales

**Conexión**:
```javascript
const token = localStorage.getItem('access_token');
const socket = new WebSocket(
    `ws://localhost:8000/ws/main/?token=${token}`
);
```

**Suscripción a grupos**:
```javascript
socket.send(JSON.stringify({
    type: 'subscribe',
    stream: 'sync_empresa_1'  // Ejemplo: sync de empresa 1
}));
```

**Recepción de mensajes**:
```javascript
socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    
    if (data.type === 'sync_update') {
        console.log('Progreso sync:', data.status, data.message);
    }
    
    if (data.type === 'general_notification') {
        console.log('Notificación:', data.message);
    }
};
```

### 8.2 JwtAuthMiddleware

Middleware custom para autenticación JWT en WebSockets.

**Ubicación**: `usuarios/middleware.py`

**Función**:
```python
@database_sync_to_async
def get_user(token_string):
    """
    Obtiene el usuario desde un Access Token JWT.
    """
    try:
        access_token = AccessToken(token_string)
        user = User.objects.get(id=access_token['user_id'])
        return user
    except (InvalidToken, TokenError, User.DoesNotExist):
        return AnonymousUser()
```

**Integración en ASGI**:
```python
# semilla360/asgi.py
from usuarios.middleware import JwtAuthMiddleware

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtAuthMiddleware(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
```

---

## 9. Recuperación de Contraseña

### 9.1 Flujo Completo

```
1. Usuario hace clic en "Olvidé mi contraseña"
   ↓
2. Frontend muestra formulario con campo "Email"
   ↓
3. Usuario ingresa email y envía
   ↓
4. POST /api/accounts/auth/password-reset/
   ↓
5. Backend valida email existe
   ↓
6. Backend genera JWT token y guarda en PasswordResetToken
   ↓
7. Backend envía email con link que contiene token
   ↓
8. Usuario recibe email y hace clic en link
   ↓
9. Frontend extrae token y user_id del query string
   ↓
10. Frontend muestra formulario para nueva contraseña
    ↓
11. Usuario ingresa nueva contraseña y confirma
    ↓
12. POST /api/accounts/auth/password-reset-confirm/
    ↓
13. Backend valida token (no expirado, activo, coincide user_id)
    ↓
14. Backend valida nueva contraseña (8+ chars, mayúscula, minúscula, número, especial)
    ↓
15. Backend actualiza contraseña con hash y marca token como inactive
    ↓
16. Frontend redirige a login con mensaje de éxito
```

### 9.2 Seguridad

**Protecciones implementadas**:
- ✅ Token expira en 15 minutos
- ✅ Token de un solo uso (`active=False` después de usar)
- ✅ Tokens antiguos invalidados al solicitar uno nuevo
- ✅ Validación de contraseña robusta (regex)
- ✅ Email con template HTML profesional
- ✅ Link con HTTPS en producción

**Recomendaciones de mejora** (Ver sección 12):
- ⚠️ Rate limiting en endpoint de solicitud
- ⚠️ CAPTCHA para evitar spam
- ⚠️ Logging de intentos de reset

---

## 10. Gestión de Empresas y Direcciones

### 10.1 Caso de Uso: Registro de Nueva Empresa

**Paso 1: Crear empresa**
```bash
POST /api/accounts/empresas/
```
```json
{
  "nombre": "AGROINDUSTRIAS SEMILLA S.A.C.",
  "direccion": "Av. Principal 123",
  "ruc": "20123456789"
}
```

**Response (201 Created)**:
```json
{
  "id": 3,
  "nombre": "AGROINDUSTRIAS SEMILLA S.A.C.",
  "direccion": "Av. Principal 123",
  "ruc": "20123456789",
  "direcciones": [],
  "state": true,
  "created_date": "2024-12-10T12:00:00Z"
}
```

**Paso 2: Agregar direcciones**
```bash
POST /api/accounts/direcciones/
```
```json
{
  "empresa": 3,
  "direccion": "Av. Los Incas 456, Oficina 301",
  "departamento": {"id": 4},  // ID de Arequipa
  "provincia": {"id": 401},
  "distrito": {"id": 40101}
}
```

**Paso 3: Consultar direcciones de la empresa**
```bash
GET /api/accounts/empresas/3/direcciones/
```

**Response**:
```json
[
  {
    "id": 10,
    "empresa": 3,
    "direccion": "Av. Los Incas 456, Oficina 301",
    "departamento": {
      "id": 4,
      "name": "Arequipa"
    },
    "provincia": {
      "id": 401,
      "name": "Arequipa"
    },
    "distrito": {
      "id": 40101,
      "name": "Arequipa"
    }
  }
]
```

---

## 11. Casos de Uso

### 11.1 Registro de Nuevo Usuario por Admin

**Contexto**: El admin de cuentas necesita crear un nuevo usuario para el módulo de importaciones.

**Flujo**:

1. **Admin hace login**:
   ```bash
   POST /api/accounts/auth/login/
   {
     "username": "admin",
     "password": "AdminPassword123!"
   }
   ```

2. **Admin obtiene lista de roles disponibles**:
   ```bash
   GET /api/accounts/roles
   ```
   Response: `[{id: 1, name: "SystemAdmin"}, {id: 2, name: "ImportacionesAdmin"}, ...]`

3. **Admin crea nuevo usuario**:
   ```bash
   POST /api/accounts/usuarios
   {
     "username": "carlos.gomez",
     "password": "Carlos123!",
     "email": "carlos.gomez@semilla360.com",
     "first_name": "Carlos",
     "last_name": "Gómez",
     "roles": [2],  // ImportacionesAdmin
     "userprofile": {
       "empresa_id": 1,
       "telefono": "+51987654321"
     }
   }
   ```

4. **Sistema crea usuario con perfil asociado**:
   - User creado con password hasheado
   - UserProfile creado con empresa y teléfono
   - Rol ImportacionesAdmin asignado

5. **Nuevo usuario puede hacer login**:
   ```bash
   POST /api/accounts/auth/login/
   {
     "username": "carlos.gomez",
     "password": "Carlos123!"
   }
   ```
   
   Response incluye roles y permisos:
   ```json
   {
     "access": "...",
     "refresh": "...",
     "user": {...},
     "roles": ["ImportacionesAdmin"],
     "permissions": {
       "importaciones.ver_fletes_internacionales": true,
       "importaciones.administrar_documentos_dua": true,
       ...
     }
   }
   ```

### 11.2 Usuario Olvida Contraseña

**Contexto**: Usuario no puede hacer login y necesita recuperar su contraseña.

**Flujo**:

1. **Usuario hace clic en "Olvidé mi contraseña"** en el frontend

2. **Usuario ingresa su email**:
   ```bash
   POST /api/accounts/auth/password-reset/
   {
     "email": "carlos.gomez@semilla360.com"
   }
   ```

3. **Sistema valida email y envía correo**:
   - Desactiva tokens anteriores
   - Genera nuevo JWT token
   - Crea registro en `PasswordResetToken` con `active=True`
   - Envía email con template HTML

4. **Usuario recibe email y hace clic en link**:
   Link: `https://semilla360.online/reset-password/confirm?token=eyJ0eXAiOiJKV1QiLCJhbGc...&user=5`

5. **Frontend extrae token y user_id, muestra formulario**

6. **Usuario ingresa nueva contraseña**:
   ```bash
   POST /api/accounts/auth/password-reset-confirm/
   {
     "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "user_id": 5,
     "new_password": "NuevaPassword123!"
   }
   ```

7. **Sistema valida y actualiza contraseña**:
   - Valida token no expirado
   - Valida token activo
   - Valida user_id coincide
   - Valida requisitos de contraseña
   - Actualiza password con hash
   - Marca token como `active=False`

8. **Usuario puede hacer login con nueva contraseña**

---

## 12. Evaluación y Mejoras Propuestas

### 12.1 Fortalezas del Módulo

#### ✅ Seguridad Robusta
- JWT con tokens de corta vida (15 min access, 7 días refresh)
- Rotación automática de refresh tokens
- Blacklist de tokens revocados
- Validación de contraseña con requisitos estrictos
- Soft-delete con auditoría completa

#### ✅ Sistema de Roles Flexible
- 6 roles predefinidos extensibles
- Permisos granulares por funcionalidad
- Fácil de agregar nuevos roles en código
- Integración con Django permissions

#### ✅ Recuperación de Contraseña Automática
- Tokens temporales de un solo uso
- Emails con template HTML profesional
- Validación robusta del flujo completo

#### ✅ Multi-empresa
- Usuarios asociados a empresas específicas
- Direcciones múltiples por empresa con ubigeo
- Aislamiento de datos por empresa

#### ✅ WebSockets para Notificaciones
- Autenticación JWT en WebSockets
- Suscripción dinámica a grupos
- Notificaciones en tiempo real

### 12.2 Áreas de Mejora Identificadas

#### 🔴 **CRÍTICO: Seguridad de Contraseñas**

**Problema**: Las contraseñas se envían en plain text en el request body.

**Riesgo**: Man-in-the-middle attack si no se usa HTTPS estricto.

**Mejora Propuesta**:
```python
# En settings.py (producción)
SECURE_SSL_REDIRECT = True  # Forzar HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

**Alternativa Avanzada**: Implementar SRP (Secure Remote Password) protocol, aunque es complejo.

#### 🟠 **ALTO: Rate Limiting**

**Problema**: No hay protección contra brute-force attacks en login y password reset.

**Riesgo**: Un atacante puede intentar miles de combinaciones de contraseñas.

**Mejora Propuesta**:
```python
# Instalar django-ratelimit
pip install django-ratelimit

# En views.py
from ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')  # 5 intentos por minuto por IP
class CustomTokenObtainPairView(TokenObtainPairView):
    ...

@ratelimit(key='ip', rate='3/h', method='POST')  # 3 intentos por hora por IP
class PasswordResetRequestView(APIView):
    ...
```

**Implementación completa**:
```python
from ratelimit.decorators import ratelimit
from ratelimit.exceptions import Ratelimited
from django.http import JsonResponse

def ratelimit_handler(request, exception):
    return JsonResponse({
        'error': 'Demasiados intentos. Por favor, espere unos minutos.'
    }, status=429)

# En settings.py
RATELIMIT_VIEW = 'usuarios.views.ratelimit_handler'
```

#### 🟠 **ALTO: Tokens en URL (Password Reset)**

**Problema**: El token se envía en query string del email.

**Riesgo**: 
- Tokens pueden quedar en logs del servidor
- Tokens pueden quedar en historial del navegador
- Referer header puede exponer token

**Mejora Propuesta**:
```python
# Opción 1: Usar código corto en vez de JWT completo
import random
import string

def generate_short_code():
    return ''.join(random.choices(string.digits, k=6))  # 6 dígitos

# En PasswordResetSerializer.save()
code = generate_short_code()
PasswordResetToken.objects.create(user=user, token=code)

reset_link = f"{settings.FRONTEND_URL}/reset-password/confirm?code={code}"
# Email muestra: "Tu código de verificación es: 123456"

# Opción 2: Usar POST en vez de GET para verificar token
# Frontend hace POST con token en body, no en URL
```

#### 🟡 **MEDIO: Logging de Eventos de Seguridad**

**Problema**: No hay registro de intentos de login fallidos, cambios de contraseña, etc.

**Riesgo**: Difícil detectar ataques o comportamiento sospechoso.

**Mejora Propuesta**:
```python
# Crear modelo para auditoría de seguridad
class SecurityAuditLog(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    event_type = models.CharField(max_length=50)  # 'login_success', 'login_failed', 'password_changed', etc.
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'security_audit_log'
        indexes = [
            models.Index(fields=['user', 'event_type', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
        ]

# En CustomTokenObtainPairView
def post(self, request, *args, **kwargs):
    try:
        response = super().post(request, *args, **kwargs)
        
        # Log login exitoso
        SecurityAuditLog.objects.create(
            user=self.user,
            event_type='login_success',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={'username': request.data.get('username')}
        )
        
        return response
    except Exception as e:
        # Log login fallido
        SecurityAuditLog.objects.create(
            event_type='login_failed',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'username': request.data.get('username'),
                'error': str(e)
            }
        )
        raise

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

#### 🟡 **MEDIO: Validación de RUC**

**Problema**: El campo `ruc` solo valida unicidad, no formato válido de SUNAT.

**Mejora Propuesta**:
```python
# En models.py o validators.py
import re

def validate_ruc(value):
    """
    Valida formato de RUC peruano (11 dígitos).
    Primeros 2 dígitos indican tipo:
    - 10: Persona Natural
    - 20: Persona Jurídica
    - 15: Entidad Pública
    - 17: Entidad Gubernamental
    """
    if not re.match(r'^(10|15|17|20)\d{9}$', value):
        raise ValidationError('RUC inválido. Debe tener 11 dígitos y comenzar con 10, 15, 17 o 20.')
    
    # Opcional: Validar dígito verificador (algoritmo de SUNAT)
    # ... (implementación del algoritmo de módulo 11)

# En Empresa model
class Empresa(BaseModel):
    ruc = models.CharField(max_length=11, unique=True, validators=[validate_ruc])
```

#### 🟡 **MEDIO: 2FA (Two-Factor Authentication)**

**Problema**: Solo se usa password (algo que sabes). No hay segundo factor (algo que tienes).

**Riesgo**: Si contraseña es comprometida, cuenta queda vulnerable.

**Mejora Propuesta**:
```python
# Instalar django-otp
pip install django-otp qrcode

# Agregar a INSTALLED_APPS
INSTALLED_APPS += [
    'django_otp',
    'django_otp.plugins.otp_totp',
]

# Crear modelo para 2FA
from django_otp.plugins.otp_totp.models import TOTPDevice

# En UserProfile, agregar:
class UserProfile(BaseModel):
    ...
    two_factor_enabled = models.BooleanField(default=False)
    
# Endpoint para activar 2FA
@api_view(['POST'])
def enable_2fa(request):
    user = request.user
    device = TOTPDevice.objects.create(user=user, name='default')
    qr_url = device.config_url  # Genera QR para Google Authenticator
    
    return Response({
        'qr_url': qr_url,
        'secret': device.key
    })

# Endpoint para verificar código 2FA en login
@api_view(['POST'])
def verify_2fa(request):
    user = request.user
    code = request.data.get('code')
    
    device = TOTPDevice.objects.get(user=user, name='default')
    if device.verify_token(code):
        return Response({'verified': True})
    return Response({'verified': False}, status=400)
```

#### 🟢 **BAJO: Paginación en Lista de Usuarios**

**Problema**: GET /api/accounts/usuarios devuelve todos los usuarios sin paginación.

**Riesgo**: Con cientos de usuarios, la respuesta puede ser lenta.

**Mejora Propuesta**:
```python
# En settings.py
REST_FRAMEWORK = {
    ...
    'PAGE_SIZE': 50,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
}

# O en el ViewSet específico
class UserViewSet(viewsets.ModelViewSet):
    ...
    pagination_class = PageNumberPagination
```

#### 🟢 **BAJO: Filtros en Lista de Usuarios**

**Problema**: No se puede filtrar usuarios por empresa, rol, activo/inactivo, etc.

**Mejora Propuesta**:
```python
# Instalar django-filter
pip install django-filter

# Crear filtro
from django_filters import rest_framework as filters

class UserFilter(filters.FilterSet):
    empresa = filters.NumberFilter(field_name='userprofile__empresa')
    role = filters.NumberFilter(field_name='groups')
    is_active = filters.BooleanFilter()
    search = filters.CharFilter(method='search_filter')
    
    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(username__icontains=value) |
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(email__icontains=value)
        )
    
    class Meta:
        model = User
        fields = ['empresa', 'role', 'is_active']

# En UserViewSet
class UserViewSet(viewsets.ModelViewSet):
    ...
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = UserFilter
    ordering_fields = ['username', 'email', 'date_joined']
```

**Uso**:
```bash
GET /api/accounts/usuarios?empresa=1&is_active=true&search=carlos&ordering=username
```

#### 🟢 **BAJO: Expiración de Sesión por Inactividad**

**Problema**: Access token expira en 15 min, pero no hay logout automático por inactividad.

**Mejora Propuesta**:
```javascript
// En frontend
let lastActivity = Date.now();

// Detectar actividad del usuario
document.addEventListener('mousemove', () => {
    lastActivity = Date.now();
});

document.addEventListener('keypress', () => {
    lastActivity = Date.now();
});

// Verificar inactividad cada minuto
setInterval(() => {
    const inactiveTime = Date.now() - lastActivity;
    const TIMEOUT = 30 * 60 * 1000;  // 30 minutos
    
    if (inactiveTime > TIMEOUT) {
        // Logout automático
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login?reason=inactivity';
    }
}, 60000);  // Cada 1 minuto
```

### 12.3 Mejoras de Arquitectura

#### **Separar Módulo de Empresas**

**Problema**: Empresas y Direcciones están en el módulo usuarios, pero se usan en otros módulos (almacen, importaciones).

**Mejora Propuesta**:
- Crear módulo `empresas` separado
- Mover modelos `Empresa` y `Direccion`
- Actualizar imports en otros módulos

**Ventajas**:
- Mejor organización
- Reduce acoplamiento
- Facilita pruebas unitarias

#### **Implementar Refresh Token Sliding Window**

**Problema**: Refresh tokens rotan en cada uso, generando muchos registros en blacklist.

**Mejora Propuesta**:
```python
# En settings.py
SIMPLE_JWT = {
    ...
    'ROTATE_REFRESH_TOKENS': False,  # Desactivar rotación
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=14),  # Sliding window de 14 días
    'SLIDING_TOKEN_LIFETIME': timedelta(days=7),
}
```

**Ventaja**: Reduce registros en blacklist, mantiene seguridad.

### 12.4 Resumen de Prioridades

| Prioridad | Mejora | Impacto | Esfuerzo |
|-----------|--------|---------|----------|
| 🔴 CRÍTICO | Forzar HTTPS en producción | Alto | Bajo |
| 🟠 ALTO | Rate limiting en login/reset | Alto | Medio |
| 🟠 ALTO | Tokens en POST body (no URL) | Medio | Medio |
| 🟡 MEDIO | Logging de seguridad | Medio | Alto |
| 🟡 MEDIO | Validación de RUC | Bajo | Bajo |
| 🟡 MEDIO | 2FA (opcional) | Alto | Alto |
| 🟢 BAJO | Paginación usuarios | Bajo | Bajo |
| 🟢 BAJO | Filtros usuarios | Bajo | Bajo |
| 🟢 BAJO | Logout por inactividad | Bajo | Bajo |

---

## Conclusión

El módulo **Usuarios** proporciona una base sólida para autenticación y autorización en Semilla360, con:

✅ **JWT robusto** con tokens de corta vida y rotación  
✅ **Sistema de roles flexible** con 6 roles predefinidos  
✅ **Recuperación de contraseña** automática con validaciones estrictas  
✅ **Multi-empresa** con soporte para direcciones múltiples  
✅ **WebSockets** para notificaciones en tiempo real  
✅ **Auditoría completa** con django-simple-history  

**Mejoras prioritarias** para implementar:
1. 🔴 Forzar HTTPS en producción
2. 🟠 Rate limiting en endpoints críticos
3. 🟠 Tokens de reset en body (no URL)
4. 🟡 Logging de eventos de seguridad
5. 🟡 Validación de RUC con algoritmo SUNAT

Con las mejoras propuestas, el módulo alcanzará estándares de seguridad nivel empresarial.

---

**Documentación creada por:** GitHub Copilot  
**Fecha:** Diciembre 2024  
**Versión del Módulo:** 1.0  
**Repositorio:** github.com/EcrDevelopment/backend_semilla360
'''
with open('DOCUMENTACION_USUARIOS_DETALLADA.md', 'w', encoding='utf-8') as f:
    f.write(content)
print('✓ Documentación usuarios completada')
"
wc -l DOCUMENTACION_USUARIOS_DETALLADA.md

