# Generated by Django 5.2.1 on 2025-07-21 02:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0007_cita_visible_para_cliente'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicio',
            name='activo',
            field=models.BooleanField(default=True, verbose_name='Activo'),
        ),
    ]
