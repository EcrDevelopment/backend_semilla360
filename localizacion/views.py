from django.contrib.auth.models import Permission
from rest_framework import generics, permissions
from .models import *
from .serializers import *

class DepartamentoListView(generics.ListAPIView):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer

class DepartamentoDetailView(generics.RetrieveAPIView):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer
    lookup_field = 'id'  # usar id como clave

# Provincias
class ProvinciaListView(generics.ListAPIView):
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer

class ProvinciaDetailView(generics.RetrieveAPIView):
    queryset = Provincia.objects.all()
    serializer_class = ProvinciaSerializer
    lookup_field = 'id'

# Distritos
class DistritoListView(generics.ListAPIView):
    queryset = Distrito.objects.all()
    serializer_class = DistritoSerializer

class DistritoDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    queryset = Distrito.objects.all()
    serializer_class = DistritoSerializer
    lookup_field = 'id'