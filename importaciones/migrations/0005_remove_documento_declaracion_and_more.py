# Generated by Django 5.0.14 on 2025-06-03 23:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('importaciones', '0004_documento_content_type_documento_object_id_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='documento',
            name='declaracion',
        ),
        migrations.RemoveField(
            model_name='historicaldocumento',
            name='declaracion',
        ),
    ]
