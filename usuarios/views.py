from collections import defaultdict
from django.contrib.contenttypes.models import ContentType
from rest_framework import status, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import PasswordResetSerializer, PasswordResetConfirmSerializer,CustomTokenObtainPairSerializer
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from .models import PasswordResetToken,Empresa,Direccion
from localizacion.models import Departamento, Provincia, Distrito
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
from django.http import JsonResponse
from django.conf import settings
from rest_framework.utils import json
from django.middleware.csrf import get_token
from rest_framework import viewsets, permissions
from django.contrib.auth.models import User, Group, Permission
from .serializers import UserSerializer, RoleSerializer, PermissionSerializer, EmpresaSerializer,DireccionSerializer
from localizacion.serializers import  DepartamentoSerializer,ProvinciaSerializer,DistritoSerializer
from rolepermissions.checkers import has_role
from rest_framework.permissions import BasePermission

def get_csrf_token(request):
    csrf_token = get_token(request)
    return JsonResponse({'csrf_Token': csrf_token})

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Correo enviado con éxito"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)

        if serializer.is_valid():
            # Obtener los datos validados
            user_id = serializer.validated_data['user_id']
            new_password = serializer.validated_data['new_password']
            token = serializer.validated_data['token']

            # Cambiar la contraseña
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()

            #Cambia estado del password
            PasswordResetToken.objects.filter(user_id=user_id).update(active=False)


            return Response({"message": "Contraseña restablecida con éxito."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response_data = serializer.validated_data
        secure = settings.DEBUG is False  # Secure solo cuando está en producción

        # Crear la respuesta
        response = Response(response_data)

        return response

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Obtener el refresh_token de las cookies
        refresh_token = request.COOKIES.get('refresh_token')

        # Si no está en las cookies, intentar obtenerlo de los parámetros de la solicitud
        if not refresh_token:
            print('no se encontro token en las cookies')
            refresh_token = request.data.get('refresh')

        # Validar que se haya encontrado el token
        if not refresh_token:
            print('no se encontro token en la request')
            return JsonResponse({'error': 'Refresh token not found'}, status=400)

        data = request.data.copy()

        data['refresh'] = refresh_token

        # Reemplazar los datos de la solicitud original con la copia mutable
        request._body = json.dumps(data)
        # Llamar al metodo original de TokenRefreshView
        return super().post(request, *args, **kwargs)

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and has_role(request.user, 'accounts_admin')

# Permission ViewSet - allow any authenticated to read
class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]  # everyone authenticated can list/retrieve perms

# Role ViewSet - only admin role
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

# User ViewSet - only admin role
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("userprofile").all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]

@api_view(['GET'])
def fetch_content_types(request):
    grouped = defaultdict(list)

    try:
        content_types = ContentType.objects.all().order_by('app_label', 'model')

        for ct in content_types:
            grouped[ct.app_label].append({
                'id': ct.id,
                'model': ct.model,
            })

        response = [
            {'app_label': app_label, 'models': models}
            for app_label, models in grouped.items()
        ]

        return Response(response)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


# Vistas para Departamento, Provincia y Distrito
class DepartamentoListView(generics.ListAPIView):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer

class ProvinciaListView(generics.ListAPIView):
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer

class DistritoListView(generics.ListAPIView):
    queryset = Distrito.objects.all()
    serializer_class = DistritoSerializer

# Vistas para Empresa y Direccion
class EmpresaListView(generics.ListCreateAPIView):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer

class EmpresaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer


class DireccionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Direccion.objects.all()
    serializer_class = DireccionSerializer

class DireccionListCreateView(generics.ListCreateAPIView):
    queryset = Direccion.objects.all()
    serializer_class = DireccionSerializer


class DireccionesPorEmpresaView(APIView):
    def get(self, request, empresa_id):
        direcciones = Direccion.objects.filter(empresa_id=empresa_id)
        serializer = DireccionSerializer(direcciones, many=True)
        return Response(serializer.data)