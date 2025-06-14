from rest_framework import serializers
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from localizacion.serializers import DepartamentoSerializer, ProvinciaSerializer, DistritoSerializer
from .models import PasswordResetToken, UserProfile, Empresa, Direccion
from  localizacion.models import  Departamento, Provincia, Distrito
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rolepermissions.roles import get_user_roles
from rolepermissions.permissions import available_perm_status
from django.contrib.auth.models import User, Group, Permission
import re


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['roles'] = [role.get_name() for role in get_user_roles(user)]
        token['permissions'] = available_perm_status(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        user_info = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'nombre': self.user.first_name,
            'apellido': self.user.last_name,
            'profile_id': None,
            'empresa_id': None
        }

        profile = getattr(self.user, 'userprofile', None)
        if profile:
            user_info['telefono'] = profile.telefono if profile.telefono else None
            user_info['empresa_id'] = profile.empresa.id if profile.empresa else None

        data['user'] = user_info
        data['roles'] = [role.get_name() for role in get_user_roles(self.user)]
        data['permissions'] = available_perm_status(self.user)

        return data

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, write_only=True)

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No existe un usuario con este correo.")
        return value

    def save(self):
        email = self.validated_data['email']
        user = User.objects.get(email=email)

        # Desactivar tokens anteriores antes de generar uno nuevo
        PasswordResetToken.objects.filter(user=user, active=True).update(active=False)

        # Generar el token de acceso JWT
        token = RefreshToken.for_user(user).access_token

        # Guardar el token y usuario en la base de datos
        PasswordResetToken.objects.create(user=user, token=token)

        # Crear el enlace de restablecimiento
        reset_link = f"{settings.FRONTEND_URL}/reset-password/confirm?token={token}&user={user.id}"
        site_name = "Semilla-360°"

        # Cargar y renderizar la plantilla HTML
        html_content = render_to_string("emails/password_reset.html", {
            'reset_link': reset_link,
            'site_name': site_name,
        })
        text_content = strip_tags(html_content)  # Genera una versión de texto plano sin HTML

        # Configurar el correo
        subject = "Restablecimiento de contraseña"
        from_email = settings.DEFAULT_FROM_EMAIL
        email_message = EmailMultiAlternatives(subject, text_content, from_email, [email])
        email_message.attach_alternative(html_content, "text/html")
        email_message.send()

class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        user = self.context['user']
        user.set_password(data['password'])
        user.save()
        return data

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    user_id = serializers.IntegerField(required=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        token = attrs.get('token')
        user_id = attrs.get('user_id')
        new_password = attrs.get('new_password')

        # Verifica la existencia del token
        try:
            token_instance = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("El token es inválido.")


        # Verifica si el token ha expirado
        if token_instance.is_expired():
            raise serializers.ValidationError("El token ha expirado, realiza una nueva solicitud.")

        # Verifica si el token esta activo
        if not token_instance.active:
            raise serializers.ValidationError("El token ya ha sido usado o invalidado.")

        # Verifica si el user_id coincide con el del token
        if token_instance.user.id != user_id:
            raise serializers.ValidationError("El usuario no coincide con el token proporcionado.")

        # Asegura que el usuario existe
        if not User.objects.filter(id=user_id).exists():
            raise serializers.ValidationError("El usuario no existe.")

        # Validación de la nueva contraseña
        if len(new_password) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r"[A-Z]", new_password):
            raise serializers.ValidationError("La contraseña debe contener al menos una letra mayúscula.")
        if not re.search(r"[a-z]", new_password):
            raise serializers.ValidationError("La contraseña debe contener al menos una letra minúscula.")
        if not re.search(r"[0-9]", new_password):
            raise serializers.ValidationError("La contraseña debe contener al menos un número.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
            raise serializers.ValidationError("La contraseña debe contener al menos un carácter especial.")

        # Si todo es válido, devuelve los atributos validados
        return attrs

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'name', 'content_type']

class RoleSerializer(serializers.ModelSerializer):  # Role == Group
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all()
    )
    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']

class UserProfileSerializer(serializers.ModelSerializer):
    empresa_id = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(),
        source="empresa",
        required=False,
        allow_null=True,
    )

    class Meta:
        model = UserProfile
        fields = ["empresa_id", "telefono"]

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    roles = serializers.PrimaryKeyRelatedField(
        many=True, source="groups", queryset=Group.objects.all(), required=False
    )
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, source="user_permissions", queryset=Permission.objects.all(), required=False
    )
    userprofile = UserProfileSerializer(required=False)  # <-- aquí va anidado

    class Meta:
        model = User
        fields = [
            "id", "username", "password", "email", "first_name", "last_name",
            "roles", "permissions", "userprofile"
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "La contraseña es obligatoria para crear un usuario."})
        return super().validate(attrs)

    def create(self, validated_data):
        roles = validated_data.pop("groups", [])
        perms = validated_data.pop("user_permissions", [])
        profile_data = validated_data.pop("userprofile", {})
        password = validated_data.pop("password")

        user = User.objects.create_user(password=password, **validated_data)
        user.groups.set(roles)
        user.user_permissions.set(perms)

        # Crear perfil asociado
        UserProfile.objects.create(user=user, **profile_data)

        return user

    def update(self, instance, validated_data):
        roles = validated_data.pop("groups", None)
        perms = validated_data.pop("user_permissions", None)
        profile_data = validated_data.pop("userprofile", {})
        print('data: ',profile_data)
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)
        instance.save()

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
        elif profile_data:  # Solo crear si hay datos en profile_data
            UserProfile.objects.create(user=instance, **profile_data)

        return instance

class DireccionSerializer(serializers.ModelSerializer):
    empresa = serializers.PrimaryKeyRelatedField(queryset=Empresa.objects.all())
    departamento = DepartamentoSerializer()
    provincia = ProvinciaSerializer()
    distrito = DistritoSerializer()

    class Meta:
        model = Direccion
        fields = '__all__'

class EmpresaSerializer(serializers.ModelSerializer):
    direcciones = DireccionSerializer(many=True, read_only=True)

    class Meta:
        model = Empresa
        fields = '__all__'



