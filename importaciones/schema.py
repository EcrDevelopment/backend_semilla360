import graphene
from .models import OrdenCompra
from graphene import ObjectType, String, Float, Mutation, Field, Decimal as GraphQLDecimal

class OrdenCompraType(ObjectType):
    id = String()
    nombre = String()
    precio = GraphQLDecimal()  # Cambiado a GraphQLDecimal
    cantidad = GraphQLDecimal()  # Cambiado a GraphQLDecimal
    fecha = String()


# Consultas
class Query(graphene.ObjectType):
    orden_compra = graphene.Field(OrdenCompraType, id=graphene.Int())
    all_orden_compras = graphene.List(OrdenCompraType)

    def resolve_orden_compra(self, info, id):
        return OrdenCompra.objects.get(pk=id)

    def resolve_all_orden_compras(self, info):
        return OrdenCompra.objects.all()

# Mutaciones
class CreateOrdenCompra(Mutation):
    class Arguments:
        nombre = String(required=True)
        precio = GraphQLDecimal(required=True)  # Cambiado a GraphQLDecimal
        cantidad = GraphQLDecimal(required=True)  # Cambiado a GraphQLDecimal

    ordenCompra = Field(OrdenCompraType)

    def mutate(self, info, nombre, precio, cantidad):
        # Aquí se crea la instancia de OrdenCompra
        orden_compra = OrdenCompra(nombre=nombre, precio=precio, cantidad=cantidad)
        orden_compra.save()
        return CreateOrdenCompra(ordenCompra=orden_compra)

class UpdateOrdenCompra(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)
        nombre = graphene.String()
        precio = graphene.Float()
        cantidad = graphene.Float()

    orden_compra = graphene.Field(OrdenCompraType)

    def mutate(self, info, id, nombre=None, precio=None, cantidad=None):
        orden_compra = OrdenCompra.objects.get(pk=id)
        if nombre:
            orden_compra.nombre = nombre
        if precio is not None:
            orden_compra.precio = precio
        if cantidad is not None:
            orden_compra.cantidad = cantidad
        orden_compra.save()
        return UpdateOrdenCompra(orden_compra=orden_compra)

class DeleteOrdenCompra(graphene.Mutation):
    class Arguments:
        id = graphene.Int(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, id):
        orden_compra = OrdenCompra.objects.get(pk=id)
        orden_compra.delete()
        return DeleteOrdenCompra(ok=True)

class Mutation(graphene.ObjectType):
    create_orden_compra = CreateOrdenCompra.Field()
    update_orden_compra = UpdateOrdenCompra.Field()
    delete_orden_compra = DeleteOrdenCompra.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
