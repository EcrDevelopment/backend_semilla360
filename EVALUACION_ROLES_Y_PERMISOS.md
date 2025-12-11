# Evaluación Crítica del Sistema de Roles y Permisos

## Fecha de Análisis
Diciembre 11, 2024

## Resumen Ejecutivo

Después de un análisis exhaustivo del sistema actual de roles y permisos, he identificado **problemas críticos de arquitectura y lógica** que están causando inconsistencias y limitando la escalabilidad del sistema. El sistema actual mezcla dos frameworks (Django Permissions y django-role-permissions) de manera incorrecta, lo que genera confusión y duplicación de lógica.

---

## 1. Problemas Identificados

### 🔴 PROBLEMA CRÍTICO #1: Mezcla Inconsistente de Dos Sistemas

**Situación Actual:**
El sistema utiliza **DOS frameworks de permisos simultáneamente** pero de manera descoordinada:

1. **Django Groups/Permissions** (nativo de Django)
2. **django-role-permissions** (biblioteca externa)

**Código Problemático:**

```python
# En serializers.py - UserSerializer
class UserSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(
        many=True, source="groups", queryset=Group.objects.all()  # Django Groups
    )
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, source="user_permissions", queryset=Permission.objects.all()  # Django Permissions
    )
```

```python
# En serializers.py - CustomTokenObtainPairSerializer
@classmethod
def get_token(cls, user):
    token = super().get_token(user)
    token['roles'] = [role.get_name() for role in get_user_roles(user)]  # django-role-permissions
    token['permissions'] = available_perm_status(user)  # django-role-permissions
    return token
```

**Problema:**
- Los roles se asignan como **Django Groups** en el CRUD de usuarios
- Pero se validan como **django-role-permissions roles** en el token JWT
- **NO hay sincronización** entre ambos sistemas
- Un usuario puede tener un Group "ImportacionesAdmin" pero NO tener el rol `ImportacionesAdmin` de django-role-permissions

**Consecuencia:**
```python
# Usuario creado con Group "ImportacionesAdmin"
user.groups.add(Group.objects.get(name="ImportacionesAdmin"))

# Pero al hacer login:
get_user_roles(user)  # Retorna [] - ¡Vacío!
# Porque django-role-permissions NO reconoce Django Groups
```

---

### 🔴 PROBLEMA CRÍTICO #2: Roles Hardcodeados sin Asignación Automática

**Situación Actual:**
Los roles están definidos en `usuarios/roles.py` pero **nunca se asignan programáticamente** a los usuarios.

**Código:**
```python
# usuarios/roles.py
class SystemAdmin(AbstractUserRole):
    available_permissions = {
        'mantenimiento.tabla_tipo_documentos': True,
    }
```

**Problema:**
- Para asignar un rol de django-role-permissions se debe llamar:
  ```python
  from rolepermissions.roles import assign_role
  assign_role(user, 'SystemAdmin')
  ```
- Este código **NO existe** en el serializer ni en las vistas
- Los usuarios se crean con Groups, no con roles de django-role-permissions
- Por tanto, `get_user_roles(user)` siempre retorna lista vacía

**Evidencia en el código:**
```python
# UserSerializer.create() - Línea 201
def create(self, validated_data):
    roles = validated_data.pop("groups", [])  # <-- Django Groups
    # ...
    user = User.objects.create_user(password=password, **validated_data)
    user.groups.set(roles)  # <-- Asigna Django Groups
    # ¡FALTA!: assign_role(user, role_name)  # django-role-permissions
```

---

### 🟠 PROBLEMA ALTO #3: Permission Class Incorrecta

**Situación Actual:**
```python
# views.py - Línea 102
class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and has_role(request.user, 'accounts_admin')
```

**Problemas:**
1. **Nombre incorrecto:** Busca rol `'accounts_admin'` (snake_case) pero la clase se llama `accountsAdmin` (camelCase)
2. **No es genérico:** Solo verifica UN rol hardcodeado
3. **Naming inconsistente:** Roles definidos como `SystemAdmin`, `ImportacionesAdmin` pero busca `accounts_admin`

**Consecuencia:**
```python
has_role(user, 'accounts_admin')  # Siempre False
# Porque el rol correcto es 'accountsAdmin' o debería ser 'AccountsAdmin'
```

---

### 🟠 PROBLEMA ALTO #4: Permisos Django No Utilizados

**Situación Actual:**
El sistema tiene una tabla completa de `auth_permission` de Django con 200+ permisos, pero:
- **NO se usan** para validar acceso a vistas
- Solo se usan en el admin de Django (que probablemente no se usa)
- django-role-permissions tiene su propio sistema de permisos (strings) que no se conecta con Django Permissions

**Código Problemático:**
```python
# ALL views in importaciones/views.py
class DespachoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]  # <-- Solo verifica autenticación
    # ¡NO valida permisos específicos!
```

**¿Qué debería ser?:**
```python
class DespachoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermission('importaciones.ver_despachos')]
```

---

### 🟡 PROBLEMA MEDIO #5: Validación de Permisos Inexistente

**Situación Actual:**
Los permisos se definen en `roles.py`:
```python
class ImportacionesAdmin(AbstractUserRole):
    available_permissions = {
        'importaciones.ver_fletes_internacionales': True,
        'importaciones.registrar_flete_internacional': True,
        # ...
    }
```

**Problema:**
- Estos permisos **NO se validan** en ninguna vista
- Son solo strings en un diccionario
- NO hay decoradores ni permission classes que los usen
- El frontend podría usarlos para ocultar/mostrar botones, pero el backend NO los valida

**Búsqueda en el código:**
```bash
grep -r "importaciones.ver_fletes_internacionales" .
# Resultado: Solo aparece en roles.py
# NO aparece en ninguna vista para validación
```

---

### 🟡 PROBLEMA MEDIO #6: Nomenclatura Inconsistente

**Inconsistencias encontradas:**

| Clase en roles.py | Nombre esperado por has_role | Frontend | Convención |
|-------------------|------------------------------|----------|------------|
| `SystemAdmin` | `'SystemAdmin'` o `'system_admin'` | ? | Inconsistente |
| `ImportacionesAdmin` | `'ImportacionesAdmin'` | ? | Inconsistente |
| `accountsAdmin` | `'accountsAdmin'` | ? | camelCase (incorrecto) |
| `accountsUser` | `'accountsUser'` | ? | camelCase (incorrecto) |

**Problema:**
- Python usa PascalCase para clases
- django-role-permissions convierte automáticamente a snake_case en algunos casos
- El código busca nombres en camelCase (`'accounts_admin'`)
- **Resultado:** Confusión total sobre qué nombre usar

---

## 2. Análisis de Impacto

### Impacto en Seguridad: 🔴 CRÍTICO

```python
# Escenario Real:
user = User.objects.create_user(username='hacker')
user.groups.add(Group.objects.get(name='SystemAdmin'))

# Token JWT dice:
token['roles'] = []  # ¡Vacío!
token['permissions'] = {}  # ¡Vacío!

# Vistas verifican:
permission_classes = [IsAuthenticated]  # ¡Solo autenticación!

# Resultado: Usuario CON Group 'SystemAdmin' pero SIN permisos reales
# Y viceversa: Usuario podría tener rol django-role-permissions pero no Group
```

**Impacto:** Sistema de autorización completamente roto.

### Impacto en Funcionalidad: 🔴 CRÍTICO

- Los roles asignados en el CRUD de usuarios **NO funcionan**
- Los permisos en el token JWT **NO reflejan la realidad**
- Las vistas **NO validan permisos** (solo autenticación)
- Sistema funciona como si **NO tuviera control de acceso**

### Impacto en Mantenibilidad: 🟠 ALTO

- Dos sistemas de permisos = Doble código
- Inconsistencias de naming = Bugs difíciles de encontrar
- Sin validación en vistas = Permisos inútiles
- Mezcla de paradigmas = Confusión para desarrolladores

---

## 3. Propuesta de Solución

### Opción A: Usar SOLO Django Groups/Permissions (Recomendado)

**Ventajas:**
- ✅ Sistema nativo de Django (bien documentado, probado)
- ✅ Integración perfecta con Django Admin
- ✅ Flexible y escalable
- ✅ Permisos a nivel de modelo automáticos
- ✅ Permite permisos custom granulares
- ✅ NO requiere biblioteca externa

**Desventajas:**
- ⚠️ Requiere refactorizar roles.py
- ⚠️ Debe eliminar django-role-permissions

**Implementación:**

```python
# 1. ELIMINAR django-role-permissions
# pip uninstall django-rolepermissions
# INSTALLED_APPS: remover 'rolepermissions'

# 2. CREAR GRUPOS CON PERMISOS
# usuarios/management/commands/setup_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # Grupo: System Admin
        system_admin, _ = Group.objects.get_or_create(name='System Admin')
        perms = Permission.objects.filter(
            codename__in=['add_tipodocumento', 'change_tipodocumento', 'delete_tipodocumento']
        )
        system_admin.permissions.set(perms)
        
        # Grupo: Importaciones Admin
        importaciones_admin, _ = Group.objects.get_or_create(name='Importaciones Admin')
        # Crear permisos custom
        content_type = ContentType.objects.get_for_model(User)
        
        perm1, _ = Permission.objects.get_or_create(
            codename='ver_fletes_internacionales',
            name='Puede ver fletes internacionales',
            content_type=content_type,
        )
        perm2, _ = Permission.objects.get_or_create(
            codename='registrar_flete_internacional',
            name='Puede registrar flete internacional',
            content_type=content_type,
        )
        # ... más permisos
        
        importaciones_admin.permissions.add(perm1, perm2)

# 3. CREAR PERMISSION CLASSES GENÉRICAS
# usuarios/permissions.py
from rest_framework.permissions import BasePermission

class HasGroupPermission(BasePermission):
    """
    Permission class que verifica si el usuario pertenece a grupos específicos.
    
    Uso en ViewSet:
        permission_classes = [HasGroupPermission]
        required_groups = ['Importaciones Admin', 'Importaciones Asistente']
    """
    def has_permission(self, request, view):
        required_groups = getattr(view, 'required_groups', [])
        if not required_groups:
            return True
        
        return request.user.groups.filter(name__in=required_groups).exists()

class HasPermission(BasePermission):
    """
    Permission class que verifica permisos específicos.
    
    Uso en ViewSet:
        permission_classes = [HasPermission]
        required_permissions = ['importaciones.ver_fletes_internacionales']
    """
    def has_permission(self, request, view):
        required_permissions = getattr(view, 'required_permissions', {})
        
        # Permite configurar permisos por método HTTP
        if isinstance(required_permissions, dict):
            method_perms = required_permissions.get(request.method, [])
        else:
            method_perms = required_permissions
        
        if not method_perms:
            return True
        
        for perm in method_perms:
            if not request.user.has_perm(perm):
                return False
        return True

# 4. USAR EN VIEWSETS
# importaciones/views.py
from usuarios.permissions import HasGroupPermission, HasPermission

class DespachoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasGroupPermission]
    required_groups = ['Importaciones Admin', 'Importaciones Asistente']
    
    # O con permisos más granulares:
    # permission_classes = [IsAuthenticated, HasPermission]
    # required_permissions = {
    #     'GET': [],  # Cualquiera autenticado puede ver
    #     'POST': ['importaciones.add_despacho'],
    #     'PUT': ['importaciones.change_despacho'],
    #     'DELETE': ['importaciones.delete_despacho'],
    # }

# 5. ACTUALIZAR SERIALIZER JWT
# usuarios/serializers.py
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Roles = Grupos de Django
        token['roles'] = list(user.groups.values_list('name', flat=True))
        
        # Permisos = Todos los permisos del usuario (vía grupos + directos)
        token['permissions'] = list(user.get_all_permissions())
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # ... user_info ...
        
        data['roles'] = list(self.user.groups.values_list('name', flat=True))
        data['permissions'] = list(self.user.get_all_permissions())
        
        return data

# 6. ACTUALIZAR VIEWS
# usuarios/views.py
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasGroupPermission]
    required_groups = ['Accounts Admin']  # Django Group
```

---

### Opción B: Usar SOLO django-role-permissions (No Recomendado)

**Ventajas:**
- ✅ Permisos como strings (fácil de leer)
- ✅ Roles definidos en código Python (no en BD)

**Desventajas:**
- ❌ NO se integra con Django Admin
- ❌ NO permite asignar permisos individuales (solo vía roles)
- ❌ Menos flexible que Django nativo
- ❌ Biblioteca externa (dependencia)
- ❌ Documentación limitada

**Implementación:**

```python
# 1. ELIMINAR uso de Django Groups
# 2. ACTUALIZAR UserSerializer
class UserSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(  # Lista de strings, no PKs
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    
    def create(self, validated_data):
        roles = validated_data.pop("roles", [])
        # ...
        user = User.objects.create_user(password=password, **validated_data)
        
        # Asignar roles de django-role-permissions
        for role_name in roles:
            assign_role(user, role_name)
        
        return user
    
    def update(self, instance, validated_data):
        roles = validated_data.pop("roles", None)
        # ...
        
        if roles is not None:
            # Eliminar roles actuales
            for role in get_user_roles(instance):
                remove_role(instance, role)
            
            # Asignar nuevos roles
            for role_name in roles:
                assign_role(instance, role_name)
        
        return instance

# 3. CREAR PERMISSION CLASS PARA PERMISOS
from rolepermissions.checkers import has_permission

class HasRolePermission(BasePermission):
    """Verifica permisos de django-role-permissions"""
    def has_permission(self, request, view):
        required_permissions = getattr(view, 'required_permissions', {})
        
        if isinstance(required_permissions, dict):
            method_perms = required_permissions.get(request.method, [])
        else:
            method_perms = required_permissions
        
        for perm in method_perms:
            if not has_permission(request.user, perm):
                return False
        return True

# 4. USAR EN VIEWSETS
class DespachoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permissions = {
        'POST': ['registrar_flete_internacional'],
        'PUT': ['editar_expedientes_dua'],
        'DELETE': ['administrar_documentos_dua'],
    }
```

---

### Opción C: Sistema Híbrido Limpio (Intermedio)

Usar Django Groups para gestión de usuarios y django-role-permissions solo para validación de permisos.

**NO RECOMENDADO** - Sigue mezclando dos sistemas.

---

## 4. Comparación de Opciones

| Criterio | Opción A (Django) | Opción B (role-permissions) | Opción C (Híbrido) |
|----------|-------------------|-----------------------------|--------------------|
| **Facilidad de implementación** | Media (refactor moderado) | Media-Alta | Baja (complejo) |
| **Integración Django** | ✅ Perfecta | ❌ Limitada | ⚠️ Parcial |
| **Escalabilidad** | ✅ Muy alta | ⚠️ Media | ❌ Baja |
| **Mantenibilidad** | ✅ Alta | ⚠️ Media | ❌ Muy baja |
| **Flexibilidad** | ✅ Muy flexible | ⚠️ Limitada | ⚠️ Confusa |
| **Documentación** | ✅ Excelente | ⚠️ Regular | ❌ Inexistente |
| **Permisos granulares** | ✅ Sí (custom) | ⚠️ Solo vía roles | ⚠️ Mixto |
| **Admin panel** | ✅ Completo | ❌ No funciona | ⚠️ Parcial |
| **Curva de aprendizaje** | ⚠️ Media | ⚠️ Media | ❌ Alta |

**Recomendación:** **Opción A - Django Nativo** ✅

---

## 5. Plan de Implementación Recomendado

### Fase 1: Preparación (1 día)

1. **Crear comando de setup de roles**
   ```bash
   python manage.py create_command setup_roles
   ```

2. **Definir todos los grupos y permisos necesarios**
   - System Admin
   - Importaciones Admin
   - Importaciones Asistente
   - Accounts Admin
   - Accounts User
   - Proveedor

3. **Crear permisos custom**
   ```python
   # Ver fletes, registrar fletes, administrar documentos, etc.
   ```

### Fase 2: Refactorización Backend (2-3 días)

1. **Actualizar `usuarios/permissions.py`**
   - Crear `HasGroupPermission`
   - Crear `HasPermission`
   - Documentar uso

2. **Actualizar `usuarios/serializers.py`**
   - Modificar `CustomTokenObtainPairSerializer`
   - Usar `user.groups.values_list()` y `user.get_all_permissions()`

3. **Actualizar `usuarios/views.py`**
   - Modificar `IsAdminRole` → `HasGroupPermission`
   - Aplicar a UserViewSet, RoleViewSet, PermissionViewSet

4. **Actualizar ViewSets en otros módulos**
   - `importaciones/views.py`: Agregar `required_groups` o `required_permissions`
   - `almacen/views.py`: Agregar validación de permisos

### Fase 3: Testing (1-2 días)

1. **Crear tests unitarios**
   ```python
   # tests/test_permissions.py
   def test_user_with_group_can_access():
       user = User.objects.create_user(username='test')
       group = Group.objects.get(name='Importaciones Admin')
       user.groups.add(group)
       
       client.force_authenticate(user=user)
       response = client.get('/api/importaciones/despachos/')
       assert response.status_code == 200
   
   def test_user_without_group_cannot_access():
       user = User.objects.create_user(username='test')
       client.force_authenticate(user=user)
       response = client.get('/api/importaciones/despachos/')
       assert response.status_code == 403
   ```

2. **Testing manual**
   - Crear usuarios con diferentes grupos
   - Verificar token JWT tiene roles y permisos correctos
   - Verificar acceso a endpoints según grupo

### Fase 4: Migración de Datos (1 día)

1. **Script de migración**
   ```python
   # Mapear nombres actuales a nuevos grupos
   ROLE_MAPPING = {
       'SystemAdmin': 'System Admin',
       'ImportacionesAdmin': 'Importaciones Admin',
       'ImportacionesAsis': 'Importaciones Asistente',
       'accountsAdmin': 'Accounts Admin',
       'accountsUser': 'Accounts User',
       'proveedor': 'Proveedor',
   }
   
   # Migrar usuarios existentes
   for user in User.objects.all():
       old_groups = user.groups.all()
       for old_group in old_groups:
           new_group_name = ROLE_MAPPING.get(old_group.name)
           if new_group_name:
               new_group = Group.objects.get(name=new_group_name)
               user.groups.add(new_group)
               user.groups.remove(old_group)
   ```

### Fase 5: Cleanup (1 día)

1. **Eliminar código obsoleto**
   - Remover `usuarios/roles.py`
   - Remover `from rolepermissions import ...`
   - Remover `'rolepermissions'` de INSTALLED_APPS

2. **Actualizar documentación**
   - README con nuevo sistema
   - Guía de creación de usuarios
   - Guía de asignación de permisos

3. **Actualizar frontend**
   - Adaptar a nueva estructura de token JWT
   - `token.roles` = array de strings (nombres de grupos)
   - `token.permissions` = array de strings ('app.codename')

---

## 6. Código de Ejemplo Completo

### setup_roles.py (Management Command)

```python
# usuarios/management/commands/setup_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Configura grupos y permisos del sistema'

    def handle(self, *args, **kwargs):
        # Content type para permisos custom
        user_ct = ContentType.objects.get_for_model(User)
        
        # ========================================
        # GRUPO: System Admin
        # ========================================
        system_admin, created = Group.objects.get_or_create(name='System Admin')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo "System Admin" creado'))
        
        # Permisos de mantenimiento
        mant_perms = Permission.objects.filter(
            codename__in=['add_tipodocumento', 'change_tipodocumento', 'delete_tipodocumento']
        )
        system_admin.permissions.set(mant_perms)
        
        # ========================================
        # GRUPO: Importaciones Admin
        # ========================================
        imp_admin, created = Group.objects.get_or_create(name='Importaciones Admin')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo "Importaciones Admin" creado'))
        
        # Crear permisos custom si no existen
        perms_to_create = [
            ('ver_fletes_internacionales', 'Puede ver fletes internacionales'),
            ('registrar_flete_internacional', 'Puede registrar flete internacional'),
            ('ver_reporte_flete', 'Puede ver reporte de fletes'),
            ('ver_reporte_estibas', 'Puede ver reporte de estibas'),
            ('administrar_documentos_dua', 'Puede administrar documentos DUA'),
            ('administrar_expedientes_dua', 'Puede administrar expedientes DUA'),
            ('editar_expedientes_dua', 'Puede editar expedientes DUA'),
            ('descargar_expedientes_dua', 'Puede descargar expedientes DUA'),
            ('agregar_mes_expedientes_dua', 'Puede agregar mes a expedientes DUA'),
            ('agregar_empresa_expedientes_dua', 'Puede agregar empresa a expedientes DUA'),
        ]
        
        imp_admin_perms = []
        for codename, name in perms_to_create:
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=user_ct,
                defaults={'name': name}
            )
            imp_admin_perms.append(perm)
            if created:
                self.stdout.write(f'  ✓ Permiso "{codename}" creado')
        
        imp_admin.permissions.set(imp_admin_perms)
        
        # ========================================
        # GRUPO: Importaciones Asistente
        # ========================================
        imp_asis, created = Group.objects.get_or_create(name='Importaciones Asistente')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo "Importaciones Asistente" creado'))
        
        # Permisos limitados (sin registrar flete, sin ver reportes)
        imp_asis_perms = Permission.objects.filter(
            codename__in=[
                'ver_fletes_internacionales',
                'administrar_documentos_dua',
                'administrar_expedientes_dua',
                'editar_expedientes_dua',
                'descargar_expedientes_dua',
                'agregar_mes_expedientes_dua',
                'agregar_empresa_expedientes_dua',
            ]
        )
        imp_asis.permissions.set(imp_asis_perms)
        
        # ========================================
        # GRUPO: Accounts Admin
        # ========================================
        acc_admin, created = Group.objects.get_or_create(name='Accounts Admin')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo "Accounts Admin" creado'))
        
        acc_perms_to_create = [
            ('listar_usuarios', 'Puede listar usuarios'),
            ('registrar_usuario', 'Puede registrar usuarios'),
            ('editar_usuario', 'Puede editar usuarios'),
        ]
        
        acc_admin_perms = []
        for codename, name in acc_perms_to_create:
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=user_ct,
                defaults={'name': name}
            )
            acc_admin_perms.append(perm)
            if created:
                self.stdout.write(f'  ✓ Permiso "{codename}" creado')
        
        acc_admin.permissions.set(acc_admin_perms)
        
        # ========================================
        # GRUPO: Accounts User
        # ========================================
        acc_user, created = Group.objects.get_or_create(name='Accounts User')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo "Accounts User" creado'))
        
        perm_editar_perfil, created = Permission.objects.get_or_create(
            codename='editar_perfil',
            content_type=user_ct,
            defaults={'name': 'Puede editar su propio perfil'}
        )
        acc_user.permissions.add(perm_editar_perfil)
        
        # ========================================
        # GRUPO: Proveedor
        # ========================================
        proveedor, created = Group.objects.get_or_create(name='Proveedor')
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Grupo "Proveedor" creado'))
        
        prov_perms_to_create = [
            ('cargar_documentos', 'Puede cargar documentos'),
            ('administrar_documentos_proveedor', 'Puede administrar sus documentos'),
        ]
        
        prov_perms = []
        for codename, name in prov_perms_to_create:
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                content_type=user_ct,
                defaults={'name': name}
            )
            prov_perms.append(perm)
            if created:
                self.stdout.write(f'  ✓ Permiso "{codename}" creado')
        
        proveedor.permissions.set(prov_perms)
        
        self.stdout.write(self.style.SUCCESS('\n✅ Setup de roles completado exitosamente'))
```

### permissions.py (Permission Classes)

```python
# usuarios/permissions.py
from rest_framework.permissions import BasePermission

class HasGroupPermission(BasePermission):
    """
    Verifica si el usuario pertenece a uno de los grupos requeridos.
    
    Uso en ViewSet/APIView:
        permission_classes = [IsAuthenticated, HasGroupPermission]
        required_groups = ['Importaciones Admin', 'Importaciones Asistente']
    
    Si required_groups está vacío o no está definido, permite el acceso.
    """
    message = 'No tienes el rol necesario para realizar esta acción.'
    
    def has_permission(self, request, view):
        required_groups = getattr(view, 'required_groups', [])
        
        # Si no hay grupos requeridos, permite el acceso
        if not required_groups:
            return True
        
        # Verifica si el usuario pertenece a alguno de los grupos
        return request.user.groups.filter(name__in=required_groups).exists()


class HasPermission(BasePermission):
    """
    Verifica si el usuario tiene los permisos específicos requeridos.
    
    Permite configurar permisos por método HTTP para mayor granularidad.
    
    Uso en ViewSet/APIView:
        # Opción 1: Permisos iguales para todos los métodos
        permission_classes = [IsAuthenticated, HasPermission]
        required_permissions = ['auth.listar_usuarios', 'auth.editar_usuario']
        
        # Opción 2: Permisos diferentes por método HTTP
        permission_classes = [IsAuthenticated, HasPermission]
        required_permissions = {
            'GET': [],  # Cualquier autenticado puede listar
            'POST': ['auth.registrar_usuario'],
            'PUT': ['auth.editar_usuario'],
            'PATCH': ['auth.editar_usuario'],
            'DELETE': ['auth.eliminar_usuario'],
        }
    """
    message = 'No tienes los permisos necesarios para realizar esta acción.'
    
    def has_permission(self, request, view):
        required_permissions = getattr(view, 'required_permissions', {})
        
        # Si es un diccionario, buscar permisos específicos del método HTTP
        if isinstance(required_permissions, dict):
            method_perms = required_permissions.get(request.method, [])
        else:
            # Si es una lista, aplicar a todos los métodos
            method_perms = required_permissions
        
        # Si no hay permisos requeridos para este método, permite el acceso
        if not method_perms:
            return True
        
        # Verifica que el usuario tenga TODOS los permisos requeridos
        for perm in method_perms:
            if not request.user.has_perm(perm):
                return False
        
        return True


class IsOwnerOrAdmin(BasePermission):
    """
    Permite acceso solo al dueño del recurso o a administradores.
    
    Uso:
        permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    Requiere que el objeto tenga un atributo 'user' o método get_owner().
    """
    message = 'Solo el propietario o un administrador puede realizar esta acción.'
    
    def has_object_permission(self, request, view, obj):
        # Admins siempre tienen acceso
        if request.user.groups.filter(name__in=['System Admin', 'Accounts Admin']).exists():
            return True
        
        # El dueño tiene acceso
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'get_owner'):
            return obj.get_owner() == request.user
        
        return False
```

### Ejemplo de Uso en ViewSets

```python
# importaciones/views.py (actualizado)
from rest_framework import viewsets, permissions
from usuarios.permissions import HasGroupPermission, HasPermission

class DespachoViewSet(viewsets.ModelViewSet):
    queryset = Despacho.objects.all()
    serializer_class = DespachoSerializer
    
    # Opción 1: Por grupos (más simple)
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    required_groups = ['Importaciones Admin', 'Importaciones Asistente']
    
    # O Opción 2: Por permisos granulares (más flexible)
    # permission_classes = [permissions.IsAuthenticated, HasPermission]
    # required_permissions = {
    #     'GET': [],  # Cualquier autenticado puede ver
    #     'POST': ['auth.administrar_documentos_dua'],
    #     'PUT': ['auth.editar_expedientes_dua'],
    #     'DELETE': ['auth.administrar_documentos_dua'],
    # }


class FleteInternacionalViewSet(viewsets.ModelViewSet):
    queryset = FleteInternacional.objects.all()
    serializer_class = FleteInternacionalSerializer
    permission_classes = [permissions.IsAuthenticated, HasPermission]
    
    # Permisos granulares por método
    required_permissions = {
        'GET': ['auth.ver_fletes_internacionales'],
        'POST': ['auth.registrar_flete_internacional'],
        'PUT': ['auth.registrar_flete_internacional'],
        'DELETE': ['auth.administrar_documentos_dua'],  # Solo admin
    }


# usuarios/views.py (actualizado)
from usuarios.permissions import HasGroupPermission

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("userprofile").all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, HasGroupPermission]
    required_groups = ['Accounts Admin']  # Solo Accounts Admin puede gestionar usuarios
```

---

## 7. Testing del Nuevo Sistema

```python
# usuarios/tests/test_permissions.py
from django.test import TestCase
from django.contrib.auth.models import User, Group
from rest_framework.test import APIClient
from rest_framework import status

class PermissionsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Crear grupos (asume que setup_roles ya corrió)
        self.imp_admin_group = Group.objects.get(name='Importaciones Admin')
        self.imp_asis_group = Group.objects.get(name='Importaciones Asistente')
        
        # Crear usuarios
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123'
        )
        self.admin_user.groups.add(self.imp_admin_group)
        
        self.asistente_user = User.objects.create_user(
            username='asistente',
            password='asistente123'
        )
        self.asistente_user.groups.add(self.imp_asis_group)
        
        self.no_group_user = User.objects.create_user(
            username='nogroup',
            password='nogroup123'
        )
    
    def test_admin_can_access_despachos(self):
        """Admin de importaciones puede acceder a despachos"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/importaciones/despachos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_asistente_can_access_despachos(self):
        """Asistente de importaciones puede acceder a despachos"""
        self.client.force_authenticate(user=self.asistente_user)
        response = self.client.get('/api/importaciones/despachos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_no_group_user_cannot_access_despachos(self):
        """Usuario sin grupo NO puede acceder a despachos"""
        self.client.force_authenticate(user=self.no_group_user)
        response = self.client.get('/api/importaciones/despachos/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_jwt_token_contains_correct_roles(self):
        """Token JWT contiene roles correctos"""
        response = self.client.post('/api/accounts/auth/login/', {
            'username': 'admin',
            'password': 'admin123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('roles', data)
        self.assertIn('Importaciones Admin', data['roles'])
        self.assertIn('permissions', data)
        self.assertIn('auth.ver_fletes_internacionales', data['permissions'])
```

---

## 8. Documentación para Desarrolladores

### Cómo Crear un Nuevo Grupo/Rol

```python
# 1. Agregar al comando setup_roles.py
nuevo_grupo, created = Group.objects.get_or_create(name='Nuevo Rol')

# 2. Crear permisos necesarios
perms_to_create = [
    ('accion_especifica', 'Puede realizar acción específica'),
]

perms = []
for codename, name in perms_to_create:
    perm, created = Permission.objects.get_or_create(
        codename=codename,
        content_type=user_ct,
        defaults={'name': name}
    )
    perms.append(perm)

nuevo_grupo.permissions.set(perms)

# 3. Ejecutar comando
python manage.py setup_roles

# 4. Asignar grupo a usuarios
user.groups.add(nuevo_grupo)
```

### Cómo Proteger un Endpoint

```python
# Opción 1: Por grupo (simple)
class MiViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasGroupPermission]
    required_groups = ['Nombre del Grupo']

# Opción 2: Por permisos granulares (flexible)
class MiViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermission]
    required_permissions = {
        'GET': [],
        'POST': ['app.permiso_crear'],
        'PUT': ['app.permiso_editar'],
        'DELETE': ['app.permiso_eliminar'],
    }

# Opción 3: Combinado
class MiViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasGroupPermission, HasPermission]
    required_groups = ['Admin']
    required_permissions = ['app.permiso_especial']
```

---

## 9. Migración de Frontend

### Antes (Actual - No Funcional)

```javascript
// Token JWT actual
{
  "access": "...",
  "refresh": "...",
  "user": {...},
  "roles": [],  // ¡Vacío! Porque django-role-permissions no está conectado
  "permissions": {}  // ¡Vacío!
}

// Código frontend (probablemente)
if (token.roles.includes('ImportacionesAdmin')) {
  // Mostrar opción
}
```

### Después (Nuevo - Funcional)

```javascript
// Token JWT nuevo
{
  "access": "...",
  "refresh": "...",
  "user": {...},
  "roles": ["Importaciones Admin", "Accounts User"],  // Array de strings (nombres de grupos)
  "permissions": [
    "auth.ver_fletes_internacionales",
    "auth.registrar_flete_internacional",
    "auth.editar_expedientes_dua",
    // ...
  ]  // Array de strings (permisos)
}

// Código frontend actualizado
if (token.roles.includes('Importaciones Admin')) {
  // Mostrar opción
}

// O verificar permiso específico
if (token.permissions.includes('auth.registrar_flete_internacional')) {
  // Mostrar botón "Registrar Flete"
}
```

**Cambios necesarios en frontend:**
- Adaptar lógica de verificación de roles (mismo concepto, diferentes nombres)
- Agregar verificación de permisos específicos si se desea más granularidad

---

## 10. Ventajas del Nuevo Sistema

### ✅ Consistencia
- Un solo sistema (Django nativo)
- Roles = Groups (sincronizados)
- Permisos validados en backend Y frontend

### ✅ Seguridad
- Permisos se validan en cada request
- NO se puede bypassear permisos (antes sí)
- Logs de auditoría con django-simple-history

### ✅ Escalabilidad
- Fácil agregar nuevos roles/permisos
- Sistema probado en millones de aplicaciones Django
- Documentación oficial extensa

### ✅ Flexibilidad
- Permisos a nivel de modelo (automáticos)
- Permisos custom (granulares)
- Permisos por objeto (IsOwnerOrAdmin)
- Combinación de permission classes

### ✅ Mantenibilidad
- Código estándar de Django
- Sin bibliotecas externas innecesarias
- Fácil de entender para cualquier dev Django

---

## 11. Desventajas y Mitigaciones

### ⚠️ Refactorización Requerida
**Mitigación:** Plan de implementación por fases (1 semana total)

### ⚠️ Cambios en Frontend
**Mitigación:** Cambios mínimos, solo adaptación de nombres

### ⚠️ Migración de Datos
**Mitigación:** Script automatizado, reversible

### ⚠️ Testing Exhaustivo
**Mitigación:** Suite de tests incluida, testing manual por fases

---

## 12. Conclusión y Recomendación Final

El sistema actual de roles y permisos tiene **problemas críticos de arquitectura** que lo hacen **no funcional** en la práctica. La mezcla de Django Groups/Permissions con django-role-permissions sin sincronización adecuada genera un sistema donde:

- Los roles asignados NO se validan
- Los permisos definidos NO se verifican
- El token JWT NO refleja la realidad
- La seguridad está comprometida

**RECOMENDACIÓN FUERTE:** Implementar **Opción A - Django Nativo** lo antes posible.

**Tiempo estimado:** 1 semana (5 días laborales)
**Impacto:** Alto (requiere testing exhaustivo)
**Beneficio:** Sistema de autorización funcional y escalable
**Riesgo:** Bajo (con testing adecuado)

---

**Autor:** GitHub Copilot  
**Fecha:** Diciembre 11, 2024  
**Versión:** 1.0  
**Estado:** Pendiente de aprobación e implementación
