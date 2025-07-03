from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta, datetime
from citas.models import Cita

class Command(BaseCommand):
    help = 'Envía recordatorios automáticos de citas'

    def handle(self, *args, **kwargs):
        ahora = timezone.now()
        limite = ahora + timedelta(hours=12)

        citas = Cita.objects.filter(
            estado__in=['pendiente', 'aceptada'],
            recordatorio_enviado=False,
            fecha__gte=ahora.date()
        )

        for cita in citas:
            fecha_hora = timezone.make_aware(datetime.combine(cita.fecha, cita.hora))
            if ahora <= fecha_hora <= limite:
                send_mail(
                    'Recordatorio de cita',
                    f'Recuerda que tienes una cita el {cita.fecha} a las {cita.hora}',
                    'noreply@tuapp.com',
                    [cita.cliente.user.email],
                    fail_silently=True
                )
                cita.recordatorio_enviado = True
                cita.save()

        self.stdout.write(self.style.SUCCESS('Recordatorios enviados correctamente.'))
