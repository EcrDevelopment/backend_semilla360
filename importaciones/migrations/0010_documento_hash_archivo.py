# Generated by Django 5.0.14 on 2025-05-06 05:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('importaciones', '0009_alter_declaracion_table_alter_documento_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='documento',
            name='hash_archivo',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
