from django.db import migrations
from django.contrib.contenttypes.models import ContentType

def asignar_content_type(apps, schema_editor):
    Documento = apps.get_model('importaciones', 'Documento')
    Declaracion = apps.get_model('importaciones', 'Declaracion')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    ct = ContentType.objects.get_for_model(Declaracion)
    for doc in Documento.objects.all():
        if doc.declaracion_id:
            doc.content_type = ct
            doc.object_id = doc.declaracion_id
            doc.save()

class Migration(migrations.Migration):

    dependencies = [
        ('importaciones', '0002_tipodocumento_historicaltipodocumento'),
    ]

    operations = [
        migrations.RunPython(asignar_content_type),
    ]