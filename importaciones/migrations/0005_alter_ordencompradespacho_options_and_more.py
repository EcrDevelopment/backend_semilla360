# Generated by Django 5.0.9 on 2025-03-12 17:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('importaciones', '0004_rename_decripcion_gastosextra_descripcion'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ordencompradespacho',
            options={},
        ),
        migrations.AddField(
            model_name='despacho',
            name='archivo_pdf',
            field=models.FileField(blank=True, null=True, upload_to='reportes_despacho/'),
        ),
        migrations.AlterField(
            model_name='ordencompradespacho',
            name='despacho',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ordenes_despacho', to='importaciones.despacho'),
        ),
    ]
