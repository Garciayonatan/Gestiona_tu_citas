# Generated by Django 5.2.1 on 2025-06-30 01:29

import datetime
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0002_empresa_nombre_empresa_alter_cliente_genero'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DiaLaborable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=5, unique=True, verbose_name='Código del Día')),
                ('nombre', models.CharField(max_length=20, unique=True, verbose_name='Nombre del Día')),
            ],
        ),
        migrations.RemoveField(
            model_name='cliente',
            name='fecha_nacimiento',
        ),
        migrations.AddField(
            model_name='cita',
            name='comentarios',
            field=models.TextField(blank=True, null=True, verbose_name='Comentarios'),
        ),
        migrations.AddField(
            model_name='cita',
            name='visible_para_empresa',
            field=models.BooleanField(default=True, help_text='Si es True, la empresa verá esta cita en su panel; si es False, no.', verbose_name='Visible para Empresa'),
        ),
        migrations.AddField(
            model_name='cliente',
            name='telegram_chat_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='empresa',
            name='cantidad_empleados',
            field=models.PositiveIntegerField(default=1, help_text='Número de empleados registrados en la empresa.', verbose_name='Cantidad de Empleados'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='capacidad',
            field=models.PositiveIntegerField(default=1, help_text='Número de personas que pueden ser atendidas al mismo tiempo en un horario.', verbose_name='Capacidad de Atención Simultánea'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='hora_cierre',
            field=models.TimeField(default=datetime.time(17, 0), verbose_name='Hora de Cierre'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='hora_inicio',
            field=models.TimeField(default=datetime.time(8, 0), verbose_name='Hora de Apertura'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='telegram_chat_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='cita',
            name='estado',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('aceptada', 'Aceptada'), ('rechazada', 'Rechazada'), ('cancelada', 'Cancelada'), ('completada', 'Completada')], default='pendiente', max_length=20, verbose_name='Estado'),
        ),
        migrations.AlterField(
            model_name='empresa',
            name='tipo_empresa',
            field=models.CharField(choices=[('Peluquería', 'Peluquería'), ('Hotel', 'Hotel'), ('Salón', 'Salón de Belleza'), ('Spa', 'Spa'), ('Barbería', 'Barbería'), ('Veterinaria', 'Veterinaria'), ('Clínica', 'Clínica'), ('Tienda', 'Tienda'), ('Centro', 'Centro')], max_length=50, verbose_name='Tipo de Empresa'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='dias_laborables',
            field=models.ManyToManyField(blank=True, related_name='empresas', to='citas.dialaborable', verbose_name='Días Laborables'),
        ),
        migrations.CreateModel(
            name='PasswordResetCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=6, verbose_name='Código')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Creado en')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Usuario')),
            ],
        ),
        migrations.CreateModel(
            name='Servicio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descripcion', models.TextField(blank=True, verbose_name='Descripción')),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Precio')),
                ('duracion', models.PositiveIntegerField(default=30, help_text='Duración aproximada del servicio en minutos.', verbose_name='Duración Estimada (minutos)')),
                ('empleados_disponibles', models.PositiveIntegerField(default=1, help_text='Número de citas que pueden atenderse al mismo tiempo.', verbose_name='Cantidad de empleados disponibles')),
                ('nombre', models.CharField(max_length=100)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='servicios', to='citas.empresa', verbose_name='Empresa')),
            ],
        ),
        migrations.AddField(
            model_name='cita',
            name='servicio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='citas.servicio'),
        ),
    ]
