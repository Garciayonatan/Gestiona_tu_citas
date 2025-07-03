from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.timezone import now, localtime, make_aware, is_naive
import datetime

# Tipos de empresa disponibles
TIPOS_EMPRESA = [
    ("Peluquería", "Peluquería"),
    ("Hotel", "Hotel"),
    ("Salón", "Salón de Belleza"),
    ("Spa", "Spa"),
    ("Barbería", "Barbería"),
    ("Veterinaria", "Veterinaria"),
    ("Clínica", "Clínica"),
    ("Tienda", "Tienda"),
    ("Centro", "Centro"),
]
#borrar
def get_default_servicio_id():
    from citas.models import Servicio
    servicio, created = Servicio.objects.get_or_create(nombre='Servicio predeterminado')
    return servicio.id  #borrar



class DiaLaborable(models.Model):
    codigo = models.CharField(max_length=5, unique=True, verbose_name="Código del Día")
    nombre = models.CharField(max_length=20, unique=True, verbose_name="Nombre del Día")

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cliente', verbose_name="Usuario")
    nombre_completo = models.CharField(max_length=150, verbose_name="Nombre Completo")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    direccion = models.CharField(max_length=255, verbose_name="Dirección", blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    genero = models.CharField(max_length=10, choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')], verbose_name="Género", blank=True, null=True)

    def __str__(self):
        return self.nombre_completo or self.user.username

class Empresa(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='empresa', verbose_name="Usuario")
    nombre_empresa = models.CharField(max_length=255, verbose_name="Nombre de la Empresa")
    nombre_dueno = models.CharField(max_length=150, verbose_name="Nombre del Dueño")
    tipo_empresa = models.CharField(max_length=50, choices=TIPOS_EMPRESA, verbose_name="Tipo de Empresa")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    direccion = models.CharField(max_length=255, verbose_name="Dirección", blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    hora_inicio = models.TimeField(default=datetime.time(8, 0), verbose_name="Hora de Apertura")
    hora_cierre = models.TimeField(default=datetime.time(17, 0), verbose_name="Hora de Cierre")
    dias_laborables = models.ManyToManyField(DiaLaborable, related_name="empresas", verbose_name="Días Laborables", blank=True)
    capacidad = models.PositiveIntegerField(default=1, verbose_name="Capacidad de Atención Simultánea", help_text="Número de personas que pueden ser atendidas al mismo tiempo en un horario.")
    cantidad_empleados = models.PositiveIntegerField(default=1, verbose_name="Cantidad de Empleados", help_text="Número de empleados registrados en la empresa.")

    def save(self, *args, **kwargs):
        self.capacidad = self.cantidad_empleados
        super().save(*args, **kwargs)

    def esta_abierta(self, ahora=None):
        ahora = ahora or localtime(now())
        dias_codigo = ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom']
        codigo_dia_actual = dias_codigo[ahora.weekday()]
        trabaja_hoy = self.dias_laborables.filter(codigo=codigo_dia_actual).exists()
        dentro_horario = self.hora_inicio <= ahora.time() <= self.hora_cierre
        return trabaja_hoy and dentro_horario

    def dias_laborables_str(self):
        return ", ".join(dia.nombre for dia in self.dias_laborables.all())

    def __str__(self):
        return f"{self.nombre_empresa} ({self.tipo_empresa})"

class Servicio(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='servicios', verbose_name="Empresa")
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Servicio")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")
    duracion = models.PositiveIntegerField(default=30, verbose_name="Duración Estimada (minutos)", help_text="Duración aproximada del servicio en minutos.")
    empleados_disponibles = models.PositiveIntegerField(default=1, verbose_name="Cantidad de empleados disponibles", help_text="Número de citas que pueden atenderse al mismo tiempo.")
    #borrae
    nombre = models.CharField(max_length=100)#borrar
    def __str__(self):
        return f"{self.nombre} - {self.empresa.nombre_empresa} (${self.precio})"

class Cita(models.Model):
    ESTADOS_CITA = [
        ("pendiente", "Pendiente"),
        ("aceptada", "Aceptada"),
        ("rechazada", "Rechazada"),
        ("cancelada", "Cancelada"),
        ("completada", "Completada")
        ("vencida", "Vencida"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='citas', verbose_name="Cliente")
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='citas', verbose_name="Empresa")
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='citas', verbose_name="Servicio")
    fecha = models.DateField(verbose_name="Fecha")
    hora = models.TimeField(verbose_name="Hora")
    comentarios = models.TextField(blank=True, null=True, verbose_name="Comentarios")
    estado = models.CharField(max_length=20, choices=ESTADOS_CITA, default="pendiente", verbose_name="Estado")
    visible_para_empresa = models.BooleanField(default=True, verbose_name="Visible para Empresa", help_text="Si es True, la empresa verá esta cita en su panel; si es False, no.")
   # primer_recordatorio_enviado = models.BooleanField(default=False)
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, null=True, blank=True)

    #segundo_recordatorio_enviado = models.BooleanField(default=False)
    def __str__(self):
        return (
            f"Cita: {self.cliente.nombre_completo} con {self.empresa.nombre_empresa} - {self.servicio.nombre} "
            f"el {self.fecha} a las {self.hora} - {self.get_estado_display()}"
        )

    def clean(self):
        hoy = localtime(now()).date()
        ahora = localtime(now()).time()

        if self.fecha < hoy:
            raise ValidationError("No se puede agendar una cita en el pasado.")
        if self.fecha == hoy and self.hora <= ahora:
            raise ValidationError("La hora de la cita debe ser en el futuro.")

        #dias_codigo = ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom']
        dias_codigo = ['LUN', 'MAR', 'MIE', 'JUE', 'VIE', 'SAB', 'DOM']
     
        codigo_dia_cita = dias_codigo[self.fecha.weekday()]
        if not self.empresa.dias_laborables.filter(codigo=codigo_dia_cita).exists():
            dia_nombre = dict((d.codigo, d.nombre) for d in DiaLaborable.objects.all()).get(codigo_dia_cita, "Día desconocido")
            raise ValidationError(f"La empresa no trabaja el día {dia_nombre} ({codigo_dia_cita}).")

        if not (self.empresa.hora_inicio <= self.hora <= self.empresa.hora_cierre):
            raise ValidationError("La hora de la cita debe estar dentro del horario laboral general de la empresa.")

    def marcar_completada_si_paso(self):
        ahora = localtime(now())
        inicio = datetime.datetime.combine(self.fecha, self.hora)

        if is_naive(inicio):
            inicio = make_aware(inicio)

        fin = inicio + datetime.timedelta(minutes=self.servicio.duracion)

        if ahora >= fin and self.estado == 'aceptada':
            self.estado = 'completada'
            self.save()

            # borrar si no funciona
    def marcar_vencida_si_paso(self):
        """Marca la cita como vencida si ya pasó y aún está pendiente."""
        ahora = localtime(now())
        inicio = datetime.datetime.combine(self.fecha, self.hora)

        if is_naive(inicio):
            #inicio = make_aware(inicio)

         if ahora >= inicio and self.estado == 'pendiente':
           self.estado = 'vencida'
           self.save()
           #aqui es para que se marque como vecida a la empresa
    

            
class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuario")
    code = models.CharField(max_length=6, verbose_name="Código")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado en")

    def is_valid(self):
        return now() < self.created_at + datetime.timedelta(minutes=15)

    def __str__(self):
        return f"Código de reinicio para {self.user.username} creado en {self.created_at}"
