# Generated by Django 5.2.1 on 2025-07-20 22:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0006_empresa_email_empresa'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='visible_para_cliente',
            field=models.BooleanField(default=True, help_text='Si es True, el cliente verá esta cita en su panel; si es False, no.', verbose_name='Visible para Cliente'),
        ),
    ]
