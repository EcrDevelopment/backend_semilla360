from django.urls import path
from .views import *

urlpatterns = [
    path('departamentos/', DepartamentoListView.as_view(), name='departamento-list'),
    path('departamentos/<str:id>/', DepartamentoDetailView.as_view(), name='departamento-detail'),

    path('provincias/', ProvinciaListView.as_view(), name='provincia-list'),
    path('provincias/<str:id>/', ProvinciaDetailView.as_view(), name='provincia-detail'),

    path('distritos/', DistritoListView.as_view(), name='distrito-list'),
    path('distritos/<str:id>/', DistritoDetailView.as_view(), name='distrito-detail'),
]