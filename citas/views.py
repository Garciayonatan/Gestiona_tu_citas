
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import UserForm, ClienteForm, EmpresaForm, EditarCitaForm
from .models import Cliente, Empresa, Cita, DiaLaborable
from datetime import datetime, time
from django.utils import timezone
from django.contrib.auth.models import User  # O usa get_user_model si es personalizado
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.core.mail import send_mail, BadHeaderError
import socket
import smtplib
import requests
from django.http import JsonResponse
from decouple import config
import logging
from .models import Servicio
from .forms import ServicioForm
from django.http import HttpResponseForbidden
from datetime import timedelta
from django.utils.timezone import make_aware
from django.views.decorators.csrf import requires_csrf_token


from telegram import Bot
from telegram.error import TelegramError
from asgiref.sync import async_to_sync
from django.utils.timezone import now
from .utils.enviar_whatsapp import enviar_whatsapp, formatear_numero
from .models import PasswordResetCode
import random  
from .forms import EditarEmpresaForm
from django.utils.timezone import is_naive, make_aware



# views.py
#from .forms import EditarCitaForm




#from app.utils import enviar_mensaje_telegram
#revisar el de abajo



# Página de inicio
#def home(request):
    #return render(request, 'app/home.html') #original chequear

def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'cliente'):
            return redirect('app:cliente_panel')  # Incluye el namespace 'app'
        elif hasattr(request.user, 'empresa'):
            return redirect('app:empresa_panel')
    return render(request, 'app/home.html')



    

# Login de usuarios

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            if hasattr(user, 'cliente'):
                messages.success(request, 'Iniciaste sesión como cliente exitosamente.')
                return redirect('app:cliente_panel')
            elif hasattr(user, 'empresa'):
                messages.success(request, 'Iniciaste sesión como empresa exitosamente.')
                return redirect('app:empresa_panel')
            else:
                messages.warning(request, 'No se pudo determinar el tipo de usuario.')
                logout(request)
                return redirect('app:login')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    # ✅ Aquí se limpian los mensajes anteriores (de otras vistas)
    storage = messages.get_messages(request)
    storage.used = True  # Marcar todos como usados y eliminar

    return render(request, 'app/login.html')

# Cierre de sesión
def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión exitosamente.')
    return redirect('app:login')

# Registro de empresa
def registro_empresa(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        empresa_form = EmpresaForm(request.POST)

        if user_form.is_valid() and empresa_form.is_valid():
            # Guardar el usuario
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data['password'])  # Cifrar contraseña
            user.save()

            # Guardar la empresa asociada al usuario
            empresa = empresa_form.save(commit=False)
            empresa.user = user
            empresa.save()
            empresa_form.save_m2m()  # Guarda relaciones many-to-many (por ejemplo, días)

            # Asignar días laborables si se reciben desde el formulario
            dias_codigos = request.POST.getlist('dias_laborables')
            if dias_codigos:
                dias = DiaLaborable.objects.filter(codigo__in=dias_codigos)
                empresa.dias_laborables.set(dias)

            # Enviar correo de confirmación
            _enviar_correo(
                asunto='Registro exitoso en Gestiona tu Cita',
                mensaje=f'Hola {user.username}, tu cuenta de empresa "{empresa.nombre_empresa}" ha sido creada correctamente.',
                destinatarios=[user.email],
            )

            messages.success(request, 'Registro exitoso. Ahora puedes iniciar sesión.')
            return redirect('app:login')
        else:
            # Mostrar errores en pantalla
            _mostrar_errores(request, user_form, empresa_form)
    else:
        user_form = UserForm()
        empresa_form = EmpresaForm()

    return render(request, 'app/register_empresa.html', {
        'user_form': user_form,
        'empresa_form': empresa_form,
        'dias': DiaLaborable.objects.all(),
    })


# Registro de cliente
# Función para enviar correos
def _enviar_correo(asunto, mensaje, destinatarios):
    try:
        send_mail(
            asunto,
            mensaje,
            'no-reply@gestionatucita.com',  # Cambia esto por tu correo remitente
            destinatarios,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error enviando correo: {e}")

# Función para mostrar errores en los formularios
def _mostrar_errores(request, *formularios):
    for formulario in formularios:
        for campo, errores in formulario.errors.items():
            for error in errores:
                messages.error(request, f"{campo}: {error}")

# Vista de registro de cliente
def registro_cliente(request):
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        cliente_form = ClienteForm(request.POST)
        if user_form.is_valid() and cliente_form.is_valid():
            email = user_form.cleaned_data.get('email').lower()
            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, 'Este correo ya está registrado. Por favor usa otro.')
            else:
                user = user_form.save(commit=False)
                user.set_password(user_form.cleaned_data.get('password'))
                user.email = email  # aseguramos guardar en minúscula
                user.save()
                cliente = cliente_form.save(commit=False)
                cliente.user = user
                cliente.save()
                _enviar_correo(
                    asunto='Bienvenido a Gestiona tu Cita',
                    mensaje=f'Hola {user.username}, tu cuenta como cliente ha sido registrada exitosamente.',
                    destinatarios=[user.email],
                )
                messages.success(request, 'Registro exitoso. Ahora puedes iniciar sesión.')
                return redirect('app:login')
        else:
            _mostrar_errores(request, user_form, cliente_form)
    else:
        user_form = UserForm()
        cliente_form = ClienteForm()
    return render(request, 'app/register_cliente.html', {
        'user_form': user_form,
        'cliente_form': cliente_form,
    })

# Panel del cliente
@login_required(login_url='app:login')
def cliente_panel(request):
    """
    Vista para mostrar el panel del cliente con sus citas y las empresas disponibles.
    También actualiza automáticamente el estado de las citas que ya han pasado.
    """
    cliente = get_object_or_404(Cliente, user=request.user)
    
    # Obtener solo las citas visibles para el cliente
    citas = Cita.objects.filter(cliente=cliente, visible_para_cliente=True).select_related('empresa', 'servicio').order_by('fecha', 'hora')

    ahora = timezone.now()

    for cita in citas:
        # Combinar fecha y hora, y asegurar que tenga zona horaria
        fecha_hora_cita = datetime.combine(cita.fecha, cita.hora)
        if is_naive(fecha_hora_cita):
            fecha_hora_cita = make_aware(fecha_hora_cita)

        if cita.estado == 'aceptada' and cita.servicio:
            # Calcular hora final del servicio
            fin_cita = fecha_hora_cita + timedelta(minutes=cita.servicio.duracion)
            if ahora >= fin_cita:
                cita.estado = 'completada'
                cita.save()

        elif cita.estado == 'pendiente' and cita.servicio:
            # Calcular hora final del servicio
            fin_cita = fecha_hora_cita + timedelta(minutes=cita.servicio.duracion)
            if ahora > fin_cita:
                cita.estado = 'vencida'
                cita.save()

    # Refrescar citas después de actualizar, filtrando por visible_para_cliente=True
    citas = Cita.objects.filter(cliente=cliente, visible_para_cliente=True).select_related('empresa', 'servicio').order_by('fecha', 'hora')
    
    empresas = Empresa.objects.prefetch_related('dias_laborables')
    dias = DiaLaborable.objects.all()

    return render(request, 'app/cliente_panel.html', {
        'cliente': cliente,
        'citas': citas,
        'empresas': empresas,
        'dias_laborables': dias,
    })

# Panel de empresa

@login_required(login_url='app:login')
def empresa_panel(request):
    if not hasattr(request.user, 'empresa'):
        return redirect('app:cliente_panel')

    empresa = request.user.empresa
    citas = Cita.objects.filter(empresa=empresa).order_by('fecha', 'hora')
    ahora = timezone.now()

    for cita in citas:
        # Combinar fecha y hora
        fecha_hora_cita = datetime.combine(cita.fecha, cita.hora)

        # Hacer timezone-aware si no lo es
        if timezone.is_naive(fecha_hora_cita):
            fecha_hora_cita = timezone.make_aware(fecha_hora_cita)

        # Actualizar estado si aplica
        if cita.estado == 'aceptada' and fecha_hora_cita <= ahora:
            cita.estado = 'completada'
            cita.save()
        elif cita.estado == 'pendiente' and fecha_hora_cita <= ahora:
            cita.estado = 'vencida'
            cita.save()

    # Citas pendientes solo
    citas_pendientes = citas.filter(estado='pendiente')
    citas_pendientes_count = citas_pendientes.count()

    dias_laborables = empresa.dias_laborables.all()
    servicios = Servicio.objects.filter(empresa=empresa)

    return render(request, 'app/empresa_panel.html', {
        'empresa': empresa,
        'citas': citas,
        'dias_laborables': dias_laborables,
        'servicios': servicios,
        'citas_pendientes': citas_pendientes,
        'citas_pendientes_count': citas_pendientes_count,  # Contador para la plantilla
    })

#telegram noti
# Configurar el logger
# Configuración del logger
import logging
import requests
import json
import re
from decouple import config
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from citas.models import Cliente, Empresa
from django.db.models import Func, F


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("telegram.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Diccionario temporal para chat_id que esperan número de teléfono
esperando_telefono = {}

def enviar_mensaje_telegram(chat_id, mensaje):
    try:
        TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TOKEN de Telegram vacío o no definido.")
    except Exception as e:
        logger.error(f"❌ No se pudo obtener el TOKEN de Telegram: {e}")
        return False

    if not chat_id or not mensaje:
        logger.error("❌ chat_id o mensaje está vacío.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    logger.info(f"📤 Intentando enviar mensaje a chat_id {chat_id}...")

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        result = response.json()

        if result.get("ok"):
            logger.info(f"✅ Mensaje enviado correctamente a chat_id {chat_id}")
            return True
        else:
            logger.error(f"❌ Telegram respondió con error: {result}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error de conexión al enviar mensaje: {e}")
        return False

@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    def post(self, request: HttpRequest):
        try:
            body = json.loads(request.body.decode('utf-8'))
            mensaje = body.get('message', {})
            texto = mensaje.get('text')
            chat_id = mensaje.get('chat', {}).get('id')

            logger.info(f"📩 Mensaje recibido: {texto} de chat_id: {chat_id}")

            if not chat_id or not texto:
                logger.warning("⚠️ chat_id o texto vacío en el mensaje recibido")
                return JsonResponse({"ok": True})

            # Verifica si ya está registrado como cliente o empresa
            cliente = Cliente.objects.filter(telegram_chat_id=chat_id).first()
            empresa = Empresa.objects.filter(telegram_chat_id=chat_id).first()

            if texto == "/start":
                if cliente:
                    enviar_mensaje_telegram(chat_id, "👤 Ya estás registrado como <b>Cliente</b>. Recibirás notificaciones aquí.")
                    return JsonResponse({"ok": True})
                elif empresa:
                    enviar_mensaje_telegram(chat_id, "🏢 Ya estás registrado como <b>Empresa</b>. Recibirás notificaciones aquí.")
                    return JsonResponse({"ok": True})
                else:
                    esperando_telefono[chat_id] = True
                    enviar_mensaje_telegram(chat_id, "📱 Bienvenido. Por favor, responde con el número de teléfono con el que te registraste (puede incluir guiones).")
                    return JsonResponse({"ok": True})

            if chat_id in esperando_telefono:
                telefono_original = texto.strip()
                telefono_limpio = re.sub(r'\D', '', telefono_original)

                if not telefono_limpio.isdigit() or len(telefono_limpio) < 5:
                    enviar_mensaje_telegram(chat_id, "❌ El número ingresado no es válido. Por favor, intenta de nuevo.")
                    return JsonResponse({"ok": True})

                logger.info(f"Buscando cliente con teléfono normalizado: {telefono_limpio}")
                cliente = None
                try:
                    cliente = Cliente.objects.annotate(
                        telefono_normalizado=Func(
                            F('telefono'),
                            function='regexp_replace',
                            template="%(function)s(%(expressions)s, '[^0-9]', '', 'g')"
                        )
                    ).filter(telefono_normalizado=telefono_limpio).first()
                except Exception as e:
                    logger.error(f"❌ Error buscando cliente: {e}")
                    cliente = None

                logger.info(f"Buscando empresa con teléfono normalizado: {telefono_limpio}")
                empresa = None
                try:
                    empresa = Empresa.objects.annotate(
                        telefono_normalizado=Func(
                            F('telefono'),
                            function='regexp_replace',
                            template="%(function)s(%(expressions)s, '[^0-9]', '', 'g')"
                        )
                    ).filter(telefono_normalizado=telefono_limpio).first()
                except Exception as e:
                    logger.error(f"❌ Error buscando empresa: {e}")
                    empresa = None

                if cliente:
                    if cliente.telegram_chat_id:
                        enviar_mensaje_telegram(chat_id, "❌ Este número ya está asociado a otro chat. Si esto es un error, contacta al soporte técnico.")
                    else:
                        cliente.telegram_chat_id = chat_id
                        cliente.save()
                        enviar_mensaje_telegram(chat_id, "✅ Registro exitoso como <b>Cliente</b>. Recibirás notificaciones aquí.")
                    esperando_telefono.pop(chat_id, None)
                    return JsonResponse({"ok": True})

                elif empresa:
                    if empresa.telegram_chat_id:
                        enviar_mensaje_telegram(chat_id, "❌ Este número ya está asociado a otro chat. Si esto es un error, contacta al soporte técnico.")
                    else:
                        empresa.telegram_chat_id = chat_id
                        empresa.save()
                        enviar_mensaje_telegram(chat_id, "✅ Registro exitoso como <b>Empresa</b>. Recibirás notificaciones aquí.")
                    esperando_telefono.pop(chat_id, None)
                    return JsonResponse({"ok": True})

                else:
                    enviar_mensaje_telegram(chat_id, "❌ Número no encontrado. Verifica o contacta al soporte.")
                    esperando_telefono.pop(chat_id, None)
                    return JsonResponse({"ok": True})

            # Para cualquier otro mensaje que no entre en las condiciones anteriores
            return JsonResponse({"ok": True})

        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class EnviarMensajeTelegramView(View):
    def post(self, request: HttpRequest):
        chat_id = request.POST.get('chat_id')
        mensaje = request.POST.get('mensaje')

        if not chat_id or not mensaje:
            logger.warning("⚠️ chat_id o mensaje faltante en la solicitud.")
            return JsonResponse({'error': 'chat_id y mensaje son requeridos.'}, status=400)

        enviado = enviar_mensaje_telegram(chat_id, mensaje)

        if enviado:
            return JsonResponse({'status': 'mensaje enviado'})
        else:
            return JsonResponse({'error': 'error enviando mensaje'}, status=500)
# Editar horario
# Editar horario
logger = logging.getLogger(__name__)

@login_required(login_url='app:login')
def editar_horario(request):
    empresa = get_object_or_404(Empresa, user=request.user)

    if request.method == 'POST':
        hora_inicio_str = request.POST.get('hora_inicio')
        hora_cierre_str = request.POST.get('hora_cierre')

        try:
            hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
            hora_cierre = datetime.strptime(hora_cierre_str, '%H:%M').time()
        except (ValueError, TypeError):
            messages.error(request, '⚠️ Formato de hora inválido.')
            return redirect('app:editar_horario')

        if hora_cierre <= hora_inicio:
            messages.error(request, '⚠️ La hora de cierre debe ser mayor que la hora de inicio.')
            return redirect('app:editar_horario')

        empresa.hora_inicio = hora_inicio
        empresa.hora_cierre = hora_cierre
        empresa.save()

        nombre_empresa = empresa.nombre_empresa
        asunto = f"Actualización de horario - {nombre_empresa}"

        hora_inicio_fmt = hora_inicio.strftime('%I:%M %p').lower()
        hora_cierre_fmt = hora_cierre.strftime('%I:%M %p').lower()

        mensaje_empresa = (
            f"<html>\n"
            f"<body style=\"font-family: Arial, sans-serif; color: #333;\">\n"
            f"<h2 style=\"color: #0056b3;\">¡Hola {empresa.nombre_dueno}!</h2>\n"
            f"<p>Queremos informarte que el horario de tu empresa <b>{nombre_empresa}</b> ha sido <b>actualizado correctamente</b>.</p>\n"
            f"<p>🔔 Aquí tienes los nuevos horarios de atención:</p>\n"
            f"<table style=\"border-collapse: collapse; margin: 20px 0;\">\n"
            f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Hora de inicio:</b></td><td style=\"padding: 8px; border: 1px solid #ddd;\">{hora_inicio_fmt}</td></tr>\n"
            f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Hora de cierre:</b></td><td style=\"padding: 8px; border: 1px solid #ddd;\">{hora_cierre_fmt}</td></tr>\n"
            f"</table>\n"
            f"<p>Gracias por mantener tu información al día. Esto ayuda a ofrecer un mejor servicio a tus clientes. 🙌</p>\n"
            f"<p style=\"color: #0056b3;\">— El equipo de Gestiona tu Cita</p>\n"
            f"</body>\n"
            f"</html>"
        )

        mensaje_telegram_empresa = (
            f"🔔 ¡Hola! Tu empresa *{nombre_empresa}* ha actualizado su horario de atención:\n"
            f"🕒 *Horario:* {hora_inicio_fmt} - {hora_cierre_fmt}\n"
            f"Gracias por mantener tu información al día con *Gestiona tu Cita* 💼"
        )

        errores = []

        try:
            send_mail(
                asunto,
                '',
                settings.DEFAULT_FROM_EMAIL,
                [empresa.user.email],
                html_message=mensaje_empresa
            )
        except Exception as e:
            logger.error(f"Error al enviar correo a la empresa: {e}")
            errores.append("correo a la empresa")

        clientes_con_citas = Cliente.objects.filter(
            citas__empresa=empresa,
            citas__estado__in=['pendiente', 'aceptada']
        ).distinct()

        for cliente in clientes_con_citas:
            nombre_cliente = cliente.nombre_completo or "cliente"

            mensaje_cliente = (
                f"<html>\n"
                f"<body style=\"font-family: Arial, sans-serif; color: #333;\">\n"
                f"<h2 style=\"color: #0056b3;\">Estimado/a {nombre_cliente},</h2>\n"
                f"<p>Queremos informarte que la empresa <b>{nombre_empresa}</b> ha actualizado su horario de atención.</p>\n"
                f"<p>🕒 Los nuevos horarios son:</p>\n"
                f"<table style=\"border-collapse: collapse; margin: 20px 0;\">\n"
                f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Hora de inicio:</b></td><td style=\"padding: 8px; border: 1px solid #ddd;\">{hora_inicio_fmt}</td></tr>\n"
                f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Hora de cierre:</b></td><td style=\"padding: 8px; border: 1px solid #ddd;\">{hora_cierre_fmt}</td></tr>\n"
                f"</table>\n"
                f"<p>Gracias por confiar en nuestros servicios.</p>\n"
                f"<p style=\"color: #0056b3;\">— El equipo de Gestiona tu Cita</p>\n"
                f"</body>\n"
                f"</html>"
            )

            if cliente.user.email:
                try:
                    send_mail(
                        asunto,
                        '',
                        settings.DEFAULT_FROM_EMAIL,
                        [cliente.user.email],
                        html_message=mensaje_cliente
                    )
                except Exception as e:
                    logger.error(f"Error al enviar correo al cliente {cliente.id}: {e}")
                    errores.append(f"correo al cliente {cliente.id}")

            if cliente.telegram_chat_id:
                try:
                    mensaje_telegram_cliente = (
                        f"👋 Hola {nombre_cliente},\n"
                        f"📢 La empresa *{nombre_empresa}* ha actualizado su horario de atención.\n"
                        f"🕒 Nuevo horario: {hora_inicio_fmt} - {hora_cierre_fmt}\n"
                        f"Gracias por preferirnos 💙"
                    )
                    enviado = enviar_mensaje_telegram(cliente.telegram_chat_id, mensaje_telegram_cliente)
                    if not enviado:
                        errores.append(f"Telegram al cliente {cliente.id}")
                except Exception as e:
                    logger.error(f"Error al enviar Telegram al cliente {cliente.id}: {e}")
                    errores.append(f"Telegram al cliente {cliente.id}")

        if empresa.telegram_chat_id:
            try:
                enviado = enviar_mensaje_telegram(empresa.telegram_chat_id, mensaje_telegram_empresa)
                if not enviado:
                    errores.append("Telegram a la empresa")
            except Exception as e:
                logger.error(f"Error al enviar Telegram a la empresa: {e}")
                errores.append("Telegram a la empresa")

        if errores:
            mensajes_errores = ', '.join(errores)
            messages.warning(request, f'⚠️ Horario actualizado, pero hubo errores con: {mensajes_errores}')
        else:
            messages.success(request, f'✅ Horario de {nombre_empresa} actualizado y notificaciones enviadas correctamente.')

        return redirect('app:empresa_panel')

    return render(request, 'app/editar_horario.html', {'empresa': empresa})

# Editar días laborables
@login_required(login_url='app:login')
def editar_dias_laborables(request):
    empresa = get_object_or_404(Empresa, user=request.user)
    dias = DiaLaborable.objects.all()

    if not dias.exists():
        messages.warning(request, '⚠️ No hay días laborables disponibles para seleccionar.')
        return redirect('app:empresa_panel')

    if request.method == 'POST':
        dias_codigos = request.POST.getlist('dias_laborables')

        if not dias_codigos:
            messages.error(request, '⚠️ Debe seleccionar al menos un día laborable.')
        else:
            dias_seleccionados = DiaLaborable.objects.filter(codigo__in=dias_codigos)
            empresa.dias_laborables.set(dias_seleccionados)
            empresa.save()

            dias_lista = ', '.join(d.nombre for d in dias_seleccionados)
            asunto = f"Actualización de días laborables - {empresa.nombre_empresa}"

            mensaje_empresa = (
                f"<html>\n"
                f"<body style=\"font-family: Arial, sans-serif; color: #333;\">\n"
                f"<h2 style=\"color: #0056b3;\">Días Laborables Actualizados</h2>\n"
                f"<p>Hola <b>{empresa.nombre_dueno}</b>,</p>\n"
                f"<p>Queremos informarte que tu empresa <b>{empresa.nombre_empresa}</b> ha actualizado sus días laborables. A continuación, te mostramos los nuevos días seleccionados:</p>\n"
                f"<p><b>{dias_lista}</b></p>\n"
                f"<p>Gracias por seguir utilizando nuestro sistema. ¡Te deseamos muchos éxitos!</p>\n"
                f"<p style=\"color: #0056b3;\">El equipo de Gestiona tu Cita</p>\n"
                f"</body>\n"
                f"</html>"
            )

            mensaje_telegram_empresa = (
                f"🏢 ¡Hola! Tu empresa <b>{empresa.nombre_empresa}</b> ha actualizado sus días laborables.\n"
                f"📅 Nuevos días activos: {dias_lista}.\n"
                f"Gracias por confiar en nosotros."
            )

            errores = []

            try:
                send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [empresa.user.email], html_message=mensaje_empresa)
            except Exception as e:
                logger.error(f"Error al enviar correo a la empresa: {e}")
                errores.append("correo a la empresa")

            clientes_con_citas = Cliente.objects.filter(
                citas__empresa=empresa,
                citas__estado__in=['pendiente', 'aceptada']
            ).distinct()

            for cliente in clientes_con_citas:
                nombre_cliente = cliente.nombre_completo or "cliente"

                mensaje_cliente = (
                    f"<html>\n"
                    f"<body style=\"font-family: Arial, sans-serif; color: #333;\">\n"
                    f"<h2 style=\"color: #0056b3;\">Actualización de Días Laborables</h2>\n"
                    f"<p>Hola <b>{nombre_cliente}</b>,</p>\n"
                    f"<p>Queremos informarte que la empresa <b>{empresa.nombre_empresa}</b> ha actualizado sus días de atención. Ahora estarán disponibles en los siguientes días:</p>\n"
                    f"<p><b>{dias_lista}</b></p>\n"
                    f"<p>Esperamos que estos cambios mejoren tu experiencia. Gracias por ser parte de Gestiona tu Cita.</p>\n"
                    f"<p style=\"color: #0056b3;\">El equipo de Gestiona tu Cita</p>\n"
                    f"</body>\n"
                    f"</html>"
                )

                if cliente.user.email:
                    try:
                        send_mail(asunto, '', settings.DEFAULT_FROM_EMAIL, [cliente.user.email], html_message=mensaje_cliente)
                    except Exception as e:
                        logger.error(f"Error al enviar correo al cliente {cliente.id}: {e}")
                        errores.append(f"correo al cliente {cliente.id}")

                if cliente.telegram_chat_id:
                    try:
                        mensaje_telegram_cliente = (
                            f"👋 ¡Hola {nombre_cliente}!,\n"
                            f"📢 La empresa {empresa.nombre_empresa} ha actualizado sus días de atención.\n"
                            f"📅 Ahora atenderán los días: {dias_lista}.\n"
                            f"¡Gracias por confiar en nosotros!"
                        )
                        enviado = enviar_mensaje_telegram(cliente.telegram_chat_id, mensaje_telegram_cliente)
                        if not enviado:
                            errores.append(f"Telegram al cliente {cliente.id}")
                    except Exception as e:
                        logger.error(f"Error al enviar Telegram al cliente {cliente.id}: {e}")
                        errores.append(f"Telegram al cliente {cliente.id}")

            if empresa.telegram_chat_id:
                try:
                    enviado = enviar_mensaje_telegram(empresa.telegram_chat_id, mensaje_telegram_empresa)
                    if not enviado:
                        errores.append("Telegram a la empresa")
                except Exception as e:
                    logger.error(f"Error al enviar Telegram a la empresa: {e}")
                    errores.append("Telegram a la empresa")

            if errores:
                mensajes_errores = ', '.join(errores)
                messages.warning(request, f'⚠️ Días actualizados, pero hubo errores con: {mensajes_errores}')
            else:
                messages.success(request, '✅ Días laborables actualizados y notificaciones enviadas correctamente.')

            return redirect('app:empresa_panel')

    return render(request, 'app/editar_laborables.html', {
        'empresa': empresa,
        'dias': dias,
        'dias_seleccionados': empresa.dias_laborables.values_list('codigo', flat=True),
    })

# Aceptar cita

logger = logging.getLogger(__name__)

@login_required(login_url='app:login')
def aceptar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)

    ahora = timezone.now()
    cita_datetime = make_aware(datetime.combine(cita.fecha, cita.hora))
    if cita.estado == 'pendiente' and cita_datetime < ahora:
        messages.error(request, '⚠️ Esta cita ya venció. Recarga la página.')
        # Si no está vencida, acepta la cita
        return redirect('app:empresa_panel')
     
    cita.estado = 'aceptada'
    cita.save()   
    


    if request.user != cita.empresa.user:
        messages.error(request, '❌ No tienes permiso para aceptar esta cita.')
        return redirect('app:empresa_panel')

    cita.estado = 'aceptada'
    cita.save()
    messages.success(request, f'✅ Cita {cita_id} aceptada correctamente.')

    asunto = f"📩 Confirmación de cita aceptada - {cita.empresa.nombre_empresa}"

    # Mensaje para el cliente
    mensaje_cliente = (
        f"Hola {cita.cliente.nombre_completo},\n\n"
        f"✅ ¡Tu cita ha sido aceptada!\n\n"
        f"👤 *Cliente:* {cita.cliente.nombre_completo}\n"
        f"🏢 *Empresa:* {cita.empresa.nombre_empresa}\n"
        f"📅 *Fecha:* {cita.fecha.strftime('%Y-%m-%d')}\n"
        f"🕒 *Hora:* {cita.hora.strftime('%I:%M %p')}\n"
        f"📌 *Estado:* {cita.get_estado_display()}\n\n"
        f"Gracias por usar nuestro sistema. 😊"
    )

    # Mensaje para la empresa
    mensaje_empresa = (
        f"Hola {cita.empresa.nombre_dueno},\n\n"
        f"✅ Has aceptado una nueva cita.\n\n"
        f"👤 *Cliente:* {cita.cliente.nombre_completo}\n"
        f"🏢 *Empresa:* {cita.empresa.nombre_empresa}\n"
        f"📅 *Fecha:* {cita.fecha.strftime('%Y-%m-%d')}\n"
        f"🕒 *Hora:* {cita.hora.strftime('%I:%M %p')}\n"
        f"📌 *Estado:* {cita.get_estado_display()}\n\n"
        f"Gracias por usar nuestro sistema. 🙌"
    )

    errores = []

    # Enviar correo al cliente
    try:
        send_mail(asunto, mensaje_cliente, settings.DEFAULT_FROM_EMAIL, [cita.cliente.user.email])
    except Exception as e:
        errores.append("correo al cliente")
        logger.error(f"Error al enviar correo al cliente: {e}")

    # Enviar correo a la empresa
    try:
        send_mail(asunto, mensaje_empresa, settings.DEFAULT_FROM_EMAIL, [cita.empresa.user.email])
    except Exception as e:
        errores.append("correo a la empresa")
        logger.error(f"Error al enviar correo a la empresa: {e}")

    # Enviar mensaje Telegram al cliente
    try:
        if cita.cliente.telegram_chat_id:
            enviar_mensaje_telegram(cita.cliente.telegram_chat_id, mensaje_cliente)
    except Exception as e:
        errores.append("Telegram al cliente")
        logger.error(f"Error al enviar Telegram al cliente: {e}")

    # Enviar mensaje Telegram a la empresa
    try:
        if cita.empresa.telegram_chat_id:
            enviar_mensaje_telegram(cita.empresa.telegram_chat_id, mensaje_empresa)
    except Exception as e:
        errores.append("Telegram a la empresa")
        logger.error(f"Error al enviar Telegram a la empresa: {e}")


           
           # Enviar WhatsApp al cliente
    #if cita.cliente.telefono:
          #enviar_whatsapp(cita.cliente.telefono, mensaje_cliente)
    #except Exception as e:
      #errores.append("WhatsApp al cliente")
      #logger.error(f"Error al enviar WhatsApp al cliente: {e}")

# Enviar WhatsApp a la empresa
    
    #  if cita.empresa.telefono:

           # enviar_whatsapp(cita.empresa.telefono, mensaje_empresa)
    #except Exception as e:
      #logger.error(f"Error al enviar WhatsApp a la empresa: {e}")
       
       #fin de mensaje de whatsapp en esta parte

    # Mostrar notificación final
    if errores:
        messages.warning(request, f"⚠️ Cita aceptada, pero hubo errores con: {', '.join(errores)}")
    else:
        messages.success(request, '✅ Todas las notificaciones fueron enviadas correctamente.')

    return redirect('app:empresa_panel')


#rechazar
@login_required(login_url='app:login')
def rechazar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)

    # Verificar que el usuario sea el dueño de la empresa
    if request.user != cita.empresa.user:
        messages.error(request, '❌ No tienes permiso para rechazar esta cita.')
        return redirect('app:empresa_panel')
        # Verificar si la cita ya venció
    ahora = now()
    cita_datetime = make_aware(datetime.combine(cita.fecha, cita.hora))
    
    if cita.estado == 'pendiente' and cita_datetime < ahora:
        messages.error(request, '⚠️ Esta cita ya venció. Recarga la página.')
        return redirect('app:empresa_panel')

    # Rechazar la cita
    cita.estado = 'rechazada'
    cita.save()

    messages.success(request, f'✅ Cita #{cita.id} rechazada correctamente.')

    nombre_empresa = cita.empresa.nombre_empresa
    nombre_cliente = cita.cliente.nombre_completo
    nombre_dueno = cita.empresa.nombre_dueno

    asunto = f"❌ Cita rechazada - {nombre_empresa}"
    fecha_str = cita.fecha.strftime('%d/%m/%Y')              
    hora_str = cita.hora.strftime('%I:%M %p')
    estado = cita.get_estado_display()

    # Mensaje para el cliente
    mensaje_cliente = (
        f"Hola {nombre_cliente},\n\n"
        f"❌ Tu cita ha sido rechazada.\n\n"
        f"👤 *Cliente:* {nombre_cliente}\n"
        f"🏢 *Empresa:* {nombre_empresa}\n"
        f"📅 *Fecha:* {fecha_str}\n"
        f"🕒 *Hora:* {hora_str}\n"
        f"📌 *Estado:* {estado}\n\n"
        f"Puedes reprogramarla en otro momento si lo deseas.\n\n"
        f"Gracias por tu comprensión y por usar nuestro sistema. 🙏"
    )

    # Mensaje para la empresa
    mensaje_empresa = (
        f"Hola {nombre_dueno},\n\n"
        f"❌ Has rechazado una cita.\n\n"
        f"👤 *Cliente:* {nombre_cliente}\n"
        f"🏢 *Empresa:* {nombre_empresa}\n"
        f"📅 *Fecha:* {fecha_str}\n"
        f"🕒 *Hora:* {hora_str}\n"
        f"📌 *Estado:* {estado}\n\n"
        f"Esta acción ha sido registrada correctamente.\n\n"
        f"Gracias por usar nuestro sistema. ✅"
    )

    errores = []

    # Notificación al cliente (correo)
    try:
        send_mail(asunto, mensaje_cliente, settings.DEFAULT_FROM_EMAIL, [cita.cliente.user.email])
    except Exception as e:
        logger.error(f"Error al enviar correo al cliente {nombre_cliente}: {e}")
        errores.append("correo al cliente")

    # Notificación a la empresa (correo)
    try:
        send_mail(asunto, mensaje_empresa, settings.DEFAULT_FROM_EMAIL, [cita.empresa.user.email])
    except Exception as e:
        logger.error(f"Error al enviar correo a la empresa {nombre_empresa}: {e}")
        errores.append("correo a la empresa")

    # Telegram al cliente
    if cita.cliente.telegram_chat_id:
        try:
            enviado = enviar_mensaje_telegram(cita.cliente.telegram_chat_id, mensaje_cliente)
            if not enviado:
                errores.append("Telegram al cliente")
        except Exception as e:
            logger.error(f"Error al enviar Telegram al cliente {nombre_cliente}: {e}")
            errores.append("Telegram al cliente")
    else:
        logger.warning(f"Cliente {nombre_cliente} no tiene chat_id de Telegram asociado.")

    # Telegram a la empresa
    if cita.empresa.telegram_chat_id:
        try:
            enviado = enviar_mensaje_telegram(cita.empresa.telegram_chat_id, mensaje_empresa)
            if not enviado:
                errores.append("Telegram a la empresa")
        except Exception as e:
            logger.error(f"Error al enviar Telegram a la empresa {nombre_empresa}: {e}")
            errores.append("Telegram a la empresa")
    else:
        logger.warning(f"Empresa {nombre_empresa} no tiene chat_id de Telegram asociado.")
                 

                    # WhatsApp al cliente
   # try:
     # if cita.cliente.telefono:
          #enviar_whatsapp(cita.cliente.telefono, mensaje_cliente)
    #except Exception as e:
      #errores.append("WhatsApp al cliente")
      #logger.error(f"Error al enviar WhatsApp al cliente {nombre_cliente}: {e}")

# WhatsApp a la empresa
   # try:
       #  if cita.empresa.telefono:
        #  enviar_whatsapp(cita.empresa.telefono, mensaje_empresa)
        
    #except Exception as e:
      #errores.append("WhatsApp a la empresa")
      #logger.error(f"Error al enviar WhatsApp a la empresa {nombre_empresa}: {e}")
       #whatsapp , aqui termina

    if errores:
        mensajes_errores = ', '.join(errores)
        messages.warning(request, f'⚠️ La cita fue rechazada, pero hubo errores con: {mensajes_errores}')
    else:
        messages.success(request, '✅ Notificaciones enviadas correctamente por correo y Telegram.')

    return redirect('app:empresa_panel')


# Cancelar cita (por el cliente)
#
#from django.contrib.auth.decorators import login_required
#from django.contrib import messages
#from .models import Cita

@login_required(login_url='app:login')
def cancelar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, cliente__user=request.user)

    if request.method == 'POST':
        if cita.estado == 'completada':
            # Evitar señales con delete directo por queryset
            Cita.objects.filter(id=cita.id).delete()
            messages.success(request, '✅ Cita completada eliminada permanentemente.')
        elif cita.estado not in ['Cancelada', 'Rechazada']:
            cita.estado = 'Cancelada'
            cita.save()
            messages.success(request, '✅ Cita cancelada correctamente.')
        else:
            messages.warning(request, '⚠️ La cita ya estaba cancelada o rechazada.')

        return redirect('app:cliente_panel')

    return render(request, 'app/cancelar_cita.html', {'cita': cita})





import logging
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import make_aware, now
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

@login_required(login_url='app:login')
def nueva_cita(request):
    cliente = get_object_or_404(Cliente, user=request.user)
    empresas = Empresa.objects.prefetch_related('dias_laborables')

    if request.method == 'POST':
        try:
            empresa_id = request.POST.get('empresa')
            servicio_id = request.POST.get('servicio')
            fecha_hora_str = request.POST.get('fecha_hora')
            comentarios = request.POST.get('comentarios', '')

            if not (empresa_id and servicio_id and fecha_hora_str):
                messages.error(request, 'Todos los campos son obligatorios.')
                return redirect('app:nueva_cita')

            empresa = Empresa.objects.get(id=empresa_id)
            servicio = Servicio.objects.get(id=servicio_id, empresa=empresa, activo=True)

            fecha_hora_naive = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M')
            fecha_hora = make_aware(fecha_hora_naive)

            confirmar_repeticion = request.POST.get('confirmar_repeticion') == '1'

            # Validar si ya completó este servicio con esta empresa el mismo día
            cita_completada = Cita.objects.filter(
                cliente=cliente,
                empresa=empresa,
                servicio=servicio,
                estado='completada',
                fecha=fecha_hora.date()
            ).exists()

            if cita_completada and not confirmar_repeticion:
                return render(request, 'app/nueva_cita.html', {
                    'empresas': empresas,
                    'servicio_repetido': True,
                    'empresa_seleccionada': empresa.id,
                    'servicio_seleccionado': servicio.id,
                    'fecha_hora': fecha_hora_str,
                    'comentarios': comentarios,
                })

            if fecha_hora < now():
                messages.error(request, 'No puedes agendar una cita en el pasado.')
                return redirect('app:nueva_cita')

            # Validar si ya tiene una cita pendiente o aceptada con esta empresa para hoy o después
            cita_activa = Cita.objects.filter(
                cliente=cliente,
                empresa=empresa,
                estado__in=['pendiente', 'aceptada'],
                fecha__gte=now().date()
            ).exists()

            if cita_activa:
                messages.warning(
                    request,
                    "⚠️ Ya tienes una cita pendiente o aceptada con esta empresa. "
                    "Debes completarla, cancelarla o reprogramarla antes de agendar una nueva."
                )
                return redirect('app:nueva_cita')

            cita_existente = Cita.objects.filter(
                cliente=cliente,
                fecha=fecha_hora.date(),
                hora=fecha_hora.time(),
                estado__in=['pendiente', 'aceptada']
            ).exists()

            if cita_existente:
                messages.error(request, 'Ya tienes una cita pendiente o aceptada a esta fecha y hora.')
                return redirect('app:nueva_cita')

            dias_semana = ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom']
            dia_codigo = dias_semana[fecha_hora.weekday()]
            dias_laborables = [d.lower() for d in empresa.dias_laborables.values_list('codigo', flat=True)]

            if dia_codigo not in dias_laborables:
                messages.error(request, 'La empresa no trabaja ese día.')
                return redirect('app:nueva_cita')

            hora_cita = fecha_hora.time()

            # ✅ Ajuste aquí: no se permite cita a la hora exacta de cierre
            if not (empresa.hora_inicio <= hora_cita < empresa.hora_cierre):
                messages.error(request, 'La hora está fuera del horario laboral.')
                return redirect('app:nueva_cita')

            fecha_hora_fin = fecha_hora + timedelta(minutes=servicio.duracion)
            citas_existentes = Cita.objects.filter(
                empresa=empresa,
                fecha=fecha_hora.date(),
                estado__in=['pendiente', 'aceptada']
            )

            citas_superpuestas = []
            for cita in citas_existentes:
                if cita.servicio is None:
                    continue

                cita_inicio = make_aware(datetime.combine(cita.fecha, cita.hora))
                cita_fin = cita_inicio + timedelta(minutes=cita.servicio.duracion)

                if not (cita_fin <= fecha_hora or fecha_hora_fin <= cita_inicio):
                    citas_superpuestas.append(cita)

            if len(citas_superpuestas) >= empresa.capacidad:
                messages.error(request, 'No hay disponibilidad para la hora seleccionada. Intenta con otro horario.')
                return redirect('app:nueva_cita')

            cita = Cita.objects.create(
                cliente=cliente,
                empresa=empresa,
                servicio=servicio,
                fecha=fecha_hora.date(),
                hora=hora_cita,
                comentarios=comentarios,
                estado='pendiente'
            )

            asunto = f"📅 Nueva cita - {empresa.nombre_empresa}"
            mensaje_cliente = (
                f"Hola {cliente.nombre_completo},\n\n"
                f"Has solicitado una nueva cita:\n"
                f"🏢 Empresa: {empresa.nombre_empresa}\n"
                f"🏷️ Tipo de Empresa: {empresa.get_tipo_empresa_display()}\n"
                f"📜 Descripción: {servicio.descripcion}\n"
                f"🕒 Duración: {servicio.duracion} minutos\n"
                f"📅 Fecha: {cita.fecha}\n"
                f"🕒 Hora: {cita.hora.strftime('%I:%M %p').lstrip('0')}\n"
                f"💼 Servicio: {servicio.nombre}\n"
                f"💰 Precio: {int(servicio.precio):,} DOP\n"
                f"📝 Comentarios: {comentarios}\n"
                f"📌 Estado: {cita.get_estado_display()}\n\n"
                f"Gracias por usar nuestro servicio."
            )
            mensaje_empresa = (
                f"Hola {empresa.nombre_dueno},\n\n"
                f"Se ha solicitado una nueva cita en tu empresa {empresa.nombre_empresa}:\n"
                f"🏷️ Tipo de Empresa: {empresa.get_tipo_empresa_display()}\n"
                f"👤 Cliente: {cliente.nombre_completo}\n"
                f"📜 Descripción del servicio: {servicio.descripcion}\n"
                f"🕒 Duración: {servicio.duracion} minutos\n"
                f"📅 Fecha: {cita.fecha}\n"
                f"🕒 Hora: {cita.hora.strftime('%I:%M %p').lstrip('0')}\n"
                f"💼 Servicio: {servicio.nombre}\n"
                f"💰 Precio: {int(servicio.precio):,} DOP\n"
                f"📝 Comentarios: {comentarios}\n"
                f"📌 Estado: {cita.get_estado_display()}\n\n"
                f"Gracias por usar nuestro servicio."
            )

            correo_ok = True
            telegram_ok = True

            try:
                send_mail(asunto, mensaje_cliente, settings.DEFAULT_FROM_EMAIL, [cliente.user.email])
                send_mail(asunto, mensaje_empresa, settings.DEFAULT_FROM_EMAIL, [empresa.user.email])
            except Exception as e:
                correo_ok = False
                logger.warning(f"⚠️ Error al enviar correos: {e}")
                messages.warning(request, "Cita creada, pero ocurrió un error al enviar los correos.")

            try:
                telegram_enviado = False
                if empresa.telegram_chat_id:
                    enviar_mensaje_telegram(empresa.telegram_chat_id, mensaje_empresa)
                    telegram_enviado = True
                if cliente.telegram_chat_id:
                    enviar_mensaje_telegram(cliente.telegram_chat_id, mensaje_cliente)
                    telegram_enviado = True
                telegram_ok = telegram_enviado
                if not telegram_enviado:
                    telegram_ok = True
            except Exception as e:
                telegram_ok = False
                logger.warning(f"⚠️ Error al enviar Telegram: {e}")
                messages.warning(request, "Cita creada, pero no se pudo enviar mensaje por Telegram.")

            if correo_ok and telegram_ok:
                messages.success(request, "✅ Cita creada correctamente. Las notificaciones se enviaron correctamente por correo y Telegram.")
            elif correo_ok and not telegram_ok:
                messages.success(request, "✅ Cita creada correctamente. Notificación enviada por correo, pero fallo el envío por Telegram.")
            elif not correo_ok and telegram_ok:
                messages.success(request, "✅ Cita creada correctamente. Notificación enviada por Telegram, pero fallo el envío por correo.")
            else:
                messages.success(request, "✅ Cita creada correctamente. No se pudieron enviar las notificaciones.")

            return redirect('app:cliente_panel')

        except Empresa.DoesNotExist:
            messages.error(request, "Empresa no encontrada.")
        except Servicio.DoesNotExist:
            messages.error(request, "Servicio no válido o no pertenece a la empresa, o está inactivo.")
        except ValueError as ve:
            messages.error(request, f"Fecha y hora inválidas: {ve}")
        except Exception as e:
            logger.error(f"❌ Error inesperado al crear cita: {e}", exc_info=True)
            messages.error(request, "❌ Ocurrió un error inesperado. Inténtalo más tarde.")

    return render(request, 'app/nueva_cita.html', {'empresas': empresas})

# El resto de funciones que mostraste (editar_cita, notificar_cita) no requieren cambios relacionados a este error.


logger = logging.getLogger(__name__)

@login_required(login_url='app:login')
def editar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, cliente__user=request.user)

    ahora = now()
    cita_datetime = datetime.combine(cita.fecha, cita.hora)
    if is_naive(cita_datetime):
        cita_datetime = make_aware(cita_datetime)

    # ✅ Actualizar estado si ya ha pasado la hora
    if cita.servicio:
        fin_cita = cita_datetime + timedelta(minutes=cita.servicio.duracion)
        if ahora >= fin_cita:
            if cita.estado == 'aceptada':
                cita.estado = 'completada'
            elif cita.estado == 'pendiente':
                cita.estado = 'vencida'
            cita.save()

    # ⛔ No permitir edición si ya está en estado no editable
    if cita.estado in ['completada', 'rechazada', 'vencida']:
        messages.error(request, f"❌ No se puede editar una cita que está {cita.estado}.")
        return redirect('app:cliente_panel')

    if request.method == 'POST':
        form = EditarCitaForm(request.POST, instance=cita)
        if form.is_valid():
            cita_nueva = form.save(commit=False)
            cita_nueva.empresa = cita.empresa
            servicio = cita_nueva.servicio

            nueva_fecha_hora = datetime.combine(cita_nueva.fecha, cita_nueva.hora)
            if is_naive(nueva_fecha_hora):
                nueva_fecha_hora = make_aware(nueva_fecha_hora)

            if nueva_fecha_hora < ahora:
                form.add_error(None, "❌ No puedes seleccionar una fecha y hora pasada.")
                return render(request, 'app/editar_cita.html', {'form': form, 'cita': cita})

            # Validar horario y día laborable
            hora_cita = cita_nueva.hora
            dias = ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom']
            dia_codigo = dias[cita_nueva.fecha.weekday()]
            dia_laboral = cita_nueva.empresa.dias_laborables.filter(codigo=dia_codigo).first()

            if not dia_laboral:
                nombre_dia = {
                    'lun': 'lunes',
                    'mar': 'martes',
                    'mie': 'miércoles',
                    'jue': 'jueves',
                    'vie': 'viernes',
                    'sab': 'sábado',
                    'dom': 'domingo',
                }.get(dia_codigo, "desconocido")
                form.add_error(None, f"⛔ La empresa no trabaja el día {nombre_dia} ({dia_codigo.upper()}).")
                return render(request, 'app/editar_cita.html', {'form': form, 'cita': cita})

            if not (cita_nueva.empresa.hora_inicio <= hora_cita <= cita_nueva.empresa.hora_cierre):
                form.add_error(None, "⛔ La hora está fuera del horario laboral de la empresa.")
                return render(request, 'app/editar_cita.html', {'form': form, 'cita': cita})

            fecha_hora_inicio = nueva_fecha_hora
            fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=servicio.duracion)

            # Verificar conflictos con otras citas del cliente
            citas_cliente = Cita.objects.filter(
                cliente=cita_nueva.cliente,
                fecha=cita_nueva.fecha,
                estado__in=['pendiente', 'aceptada']
            ).exclude(id=cita.id)

            for otra in citas_cliente:
                otra_inicio = make_aware(datetime.combine(otra.fecha, otra.hora)) if is_naive(datetime.combine(otra.fecha, otra.hora)) else datetime.combine(otra.fecha, otra.hora)
                otra_fin = otra_inicio + timedelta(minutes=otra.servicio.duracion)
                if fecha_hora_inicio < otra_fin and fecha_hora_fin > otra_inicio:
                    form.add_error(None, "❌ Ya tienes una cita en ese horario.")
                    return render(request, 'app/editar_cita.html', {'form': form, 'cita': cita})

            # Verificar conflictos con otras citas de la empresa
            citas_empresa = Cita.objects.filter(
                empresa=cita_nueva.empresa,
                fecha=cita_nueva.fecha,
                estado__in=['pendiente', 'aceptada']
            ).exclude(id=cita.id)

            conflictos = 0
            for otra in citas_empresa:
                otra_inicio = make_aware(datetime.combine(otra.fecha, otra.hora)) if is_naive(datetime.combine(otra.fecha, otra.hora)) else datetime.combine(otra.fecha, otra.hora)
                otra_fin = otra_inicio + timedelta(minutes=otra.servicio.duracion)
                if fecha_hora_inicio < otra_fin and fecha_hora_fin > otra_inicio:
                    conflictos += 1

            if conflictos >= cita_nueva.empresa.capacidad:
                form.add_error(None, "❌ Ya hay otras citas que se cruzan con ese horario.")
                return render(request, 'app/editar_cita.html', {'form': form, 'cita': cita})

            cita_nueva.save()

            resultados = notificar_cita(
                cita_nueva,
                cita_nueva.cliente,
                cita_nueva.empresa,
                servicio,
                cita_nueva.comentarios,
                "actualizada"
            )

            mensaje = "✅ Cita actualizada correctamente."
            if resultados["email_cliente"] or resultados["email_empresa"]:
                mensaje += " 📧 Notificaciones enviadas por correo electrónico."
            if resultados["telegram_cliente"] or resultados["telegram_empresa"]:
                mensaje += " 📲 Notificaciones enviadas por Telegram."

            messages.success(request, mensaje)
            return redirect('app:cliente_panel')

        else:
            messages.error(request, "❌ Por favor, corrige los errores del formulario.")
            logger.error(f"Errores en formulario editar_cita: {form.errors}")
    else:
        form = EditarCitaForm(instance=cita)

    return render(request, 'app/editar_cita.html', {'form': form, 'cita': cita})


def notificar_cita(cita, cliente, empresa, servicio, comentarios, accion):
    comentarios = comentarios.strip() if comentarios else "Sin comentarios"
    asunto = f"Cita {accion.capitalize()} - {empresa.nombre_empresa}"

    mensajes = {
        "cliente": (
            f"Hola {cliente.nombre_completo},\n\n"
            f"Tu cita ha sido {accion}:\n"
            f"🏢 Empresa: {empresa.nombre_empresa}\n"
            f"🏷️ Tipo de Empresa: {empresa.get_tipo_empresa_display()}\n"
            f"📜 Descripción: {servicio.descripcion}\n"
            f"🕒 Duración: {servicio.duracion} minutos\n"
            f"💰 Precio: {int(servicio.precio):,} DOP\n"
            f"📅 Fecha: {cita.fecha}\n"
            f"🕒 Hora: {cita.hora.strftime('%I:%M %p').lstrip('0')}\n"
            f"💼 Servicio: {servicio.nombre}\n"
            f"📝 Comentarios: {comentarios}\n"
            f"📌 Estado: {cita.get_estado_display()}\n\n"
            f"Gracias por usar nuestro servicio."
        ),
        "empresa": (
            f"Hola {empresa.nombre_dueno},\n\n"
            f"Se ha actualizado una cita en tu empresa {empresa.nombre_empresa}:\n"
            f"🏷️ Tipo de Empresa: {empresa.get_tipo_empresa_display()}\n"
            f"👤 Cliente: {cliente.nombre_completo}\n"
            f"📜 Descripción: {servicio.descripcion}\n"
            f"🕒 Duración: {servicio.duracion} minutos\n"
            f"💰 Precio: {int(servicio.precio):,} DOP\n"
            f"📅 Fecha: {cita.fecha}\n"
            f"🕒 Hora: {cita.hora.strftime('%I:%M %p').lstrip('0')}\n"
            f"💼 Servicio: {servicio.nombre}\n"
            f"📝 Comentarios: {comentarios}\n"
            f"📌 Estado: {cita.get_estado_display()}\n\n"
            f"Gracias por usar nuestro sistema."
        )
    }

    resultados = {
        "email_cliente": False,
        "email_empresa": False,
        "telegram_cliente": False,
        "telegram_empresa": False,
    }

    try:
        if cliente.user.email:
            send_mail(asunto, mensajes["cliente"], settings.DEFAULT_FROM_EMAIL, [cliente.user.email])
            resultados["email_cliente"] = True
        if empresa.user.email:
            send_mail(asunto, mensajes["empresa"], settings.DEFAULT_FROM_EMAIL, [empresa.user.email])
            resultados["email_empresa"] = True
    except Exception as e:
        logger.error(f"Error al enviar correos: {e}")

    try:
        if cliente.telegram_chat_id:
            enviar_mensaje_telegram(cliente.telegram_chat_id, mensajes["cliente"])
            resultados["telegram_cliente"] = True
        if empresa.telegram_chat_id:
            enviar_mensaje_telegram(empresa.telegram_chat_id, mensajes["empresa"])
            resultados["telegram_empresa"] = True
    except Exception as e:
        logger.error(f"Error al enviar mensajes por Telegram: {e}")

    return resultados
    
@login_required(login_url='app:login')
def eliminar_cita(request, cita_id):
    try:
        cita = Cita.objects.get(id=cita_id, cliente__user=request.user)
    except Cita.DoesNotExist:
        messages.error(request, "❌ Esta cita ya fue eliminada o no existe.")
        return redirect('app:cliente_panel')

    if request.method == 'POST':
        ahora = timezone.now()
        cita_datetime = timezone.make_aware(
            datetime.combine(cita.fecha, cita.hora),
            timezone.get_current_timezone()
        )

        # Validar que no se pueda eliminar si está aceptada y faltan 20 minutos o menos
        if cita.estado == 'aceptada' and (cita_datetime - ahora) <= timedelta(minutes=20):
            messages.error(
                request,
                "🚫 No puedes eliminar una cita aceptada si faltan 20 minutos o menos para su inicio."
            )
            return redirect('app:cliente_panel')

        cliente = request.user
        cliente_nombre = cita.cliente.nombre_completo or cliente.username
        cliente_email = cliente.email
        cliente_chat_id = cita.cliente.telegram_chat_id

        empresa = cita.empresa
        empresa_nombre = empresa.nombre_empresa
        empresa_email = empresa.user.email
        empresa_chat_id = empresa.telegram_chat_id
        empresa_dueno = empresa.nombre_dueno

        fecha = cita.fecha
        hora = cita.hora
        estado = cita.estado

        # En vez de eliminar, ocultamos la cita y la marcamos como cancelada
        #cita.visible_para_cliente = False
        #cita.estado = 'cancelada'
        #cita.save()

        # En vez de eliminar, ocultamos la cita
        cita.visible_para_cliente = False
       # Solo cambiamos el estado si no es completada ni vencida
        if cita.estado not in ['completada', 'vencida']:
           cita.estado = 'cancelada'
        cita.save()


        messages.success(request, '✅ Cita eliminada (exitosamente).')

        # Si la cita estaba completada o vencida, no enviamos notificaciones
        if estado in ['completada', 'vencida']:
            return redirect('app:cliente_panel')

        if estado != 'rechazada':
            errores = []

            fecha_str = fecha.strftime('%d/%m/%Y')  # Formato amigable: 22/06/2025
            hora_str = hora.strftime('%I:%M %p')    # Formato 12h: 08:01 PM

            asunto_cliente = "📩 Confirmación de cancelación de cita"
            asunto_empresa = "📢 Notificación de cita cancelada por el cliente"

            mensaje_cliente = (
                f"Hola {cliente_nombre},\n\n"
                f"❌ Has cancelado tu cita con {empresa_nombre}.\n\n"
                f"👤 *Cliente:* {cliente_nombre}\n"
                f"🏢 *Empresa:* {empresa_nombre}\n"
                f"🏷️ Tipo de Empresa: {empresa.get_tipo_empresa_display()}\n"
                f"📅 *Fecha:* {fecha_str}\n"
                f"🕒 *Hora:* {hora_str}\n"
                f"📌 *Estado:* Cancelada\n\n"
                f"Gracias por usar nuestro sistema. 😊"
            )

            mensaje_empresa = (
                f"Hola {empresa_dueno},\n\n"
                f"❌ El cliente ha cancelado una cita.\n\n"
                f"👤 *Cliente:* {cliente_nombre}\n"
                f"🏢 *Empresa:* {empresa_nombre}\n"
                f"🏷️ Tipo de Empresa: {empresa.get_tipo_empresa_display()}\n"
                f"📅 *Fecha:* {fecha_str}\n"
                f"🕒 *Hora:* {hora_str}\n"
                f"📌 *Estado:* Cancelada\n\n"
                f"Gracias por usar nuestro sistema. 🙌"
            )

            # Enviar correos
            try:
                if cliente_email:
                    send_mail(
                        subject=asunto_cliente,
                        message=mensaje_cliente,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[cliente_email]
                    )
            except Exception as e:
                logger.error(f"Error al enviar correo al cliente: {e}")
                errores.append("correo al cliente")

            try:
                if empresa_email:
                    send_mail(
                        subject=asunto_empresa,
                        message=mensaje_empresa,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[empresa_email]
                    )
            except Exception as e:
                logger.error(f"Error al enviar correo a la empresa: {e}")
                errores.append("correo a la empresa")

            # Enviar mensajes por Telegram
            try:
                if cliente_chat_id:
                    enviado = enviar_mensaje_telegram(cliente_chat_id, mensaje_cliente)
                    if not enviado:
                        errores.append("Telegram al cliente")
            except Exception as e:
                logger.error(f"Error al enviar Telegram al cliente: {e}")
                errores.append("Telegram al cliente")

            try:
                if empresa_chat_id:
                    enviado = enviar_mensaje_telegram(empresa_chat_id, mensaje_empresa)
                    if not enviado:
                        errores.append("Telegram a la empresa")
            except Exception as e:
                logger.error(f"Error al enviar Telegram a la empresa: {e}")
                errores.append("Telegram a la empresa")

            if errores:
                messages.warning(request, f"⚠️ Cita eliminada, pero fallaron: {', '.join(errores)}")
            else:
                messages.success(request, "📬 Correo enviado | 📲 Telegram enviado correctamente.")

        return redirect('app:cliente_panel')


# servicios administrar 
def formatear_precio(precio):
    try:
        valor = int(round(precio))
        return f"RD$ {valor:,}".replace(",", ",")
    except:
        return "RD$ 0"

@login_required
def administrar_servicios(request):
    """
    Vista para administrar los servicios de una empresa.
    Permite agregar, listar, ocultar (desactivar) y mostrar (activar) servicios, 
    así como actualizar la capacidad de empleados.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return HttpResponseForbidden("No tienes una empresa asociada para gestionar servicios.")

    empleados_rango = range(1, 101)
    form = ServicioForm()

    if request.method == 'POST':
        if 'eliminar_servicio' in request.POST:
            servicio_id = request.POST.get('servicio_id')
            try:
                servicio = Servicio.objects.get(id=servicio_id, empresa=empresa)
                servicio.activo = False  # Ocultar el servicio en lugar de borrarlo
                servicio.save()
                messages.success(request, "Servicio ocultado correctamente.")
            except Servicio.DoesNotExist:
                messages.error(request, "El servicio que intentas ocultar no existe.")
            return redirect('app:servicios_empresa')

        elif 'mostrar_servicio' in request.POST:
            servicio_id = request.POST.get('servicio_id')
            try:
                servicio = Servicio.objects.get(id=servicio_id, empresa=empresa)
                servicio.activo = True  # Activar el servicio nuevamente
                servicio.save()
                messages.success(request, "Servicio activado correctamente.")
            except Servicio.DoesNotExist:
                messages.error(request, "El servicio que intentas activar no existe.")
            return redirect('app:servicios_empresa')

        elif 'cantidad_empleados' in request.POST:
            cantidad_empleados = request.POST.get('cantidad_empleados')
            if cantidad_empleados and cantidad_empleados.isdigit():
                empresa.cantidad_empleados = int(cantidad_empleados)
                empresa.save()
                messages.success(request, "Cantidad de empleados actualizada correctamente.")
            else:
                messages.error(request, "Cantidad de empleados inválida.")
            return redirect('app:servicios_empresa')

        else:
            form = ServicioForm(request.POST)
            if form.is_valid():
                nuevo_servicio = form.save(commit=False)
                nuevo_servicio.empresa = empresa
                nuevo_servicio.save()
                messages.success(request, "Servicio agregado correctamente.")
                return redirect('app:servicios_empresa')
            else:
                messages.error(request, "Error al agregar el servicio. Verifique los datos.")

    # Separar servicios activos y ocultos
    servicios_activos = Servicio.objects.filter(empresa=empresa, activo=True)
    servicios_ocultos = Servicio.objects.filter(empresa=empresa, activo=False)

    # Formatear los precios
    for s in servicios_activos:
        s.precio_formateado = formatear_precio(s.precio)
    for s in servicios_ocultos:
        s.precio_formateado = formatear_precio(s.precio)

    return render(request, 'app/servicio_empresa.html', {
        'empresa': empresa,
        'form': form,
        'servicios_activos': servicios_activos,
        'servicios_ocultos': servicios_ocultos,
        'empleados_rango': empleados_rango,
        'cantidad_empleados': empresa.cantidad_empleados,
    })

          #derigir si no tiene empresa


#cita eliminar empresa
# views.py

@login_required(login_url='login')  # Asegura que el usuario esté logueado
def empresa_panel(request):
    """
    Muestra el panel de la empresa, listando únicamente las citas
    cuya bandera visible_para_empresa esté en True.
    Si el usuario no tiene empresa asociada, lo redirige al home.
    """
    try:
        empresa = Empresa.objects.get(user=request.user)
    except Empresa.DoesNotExist:
        return redirect('home')  # Si no tiene empresa, lo manda al home

    # Obtener citas pendientes visibles para la empresa
    citas_pendientes = Cita.objects.filter(
        empresa=empresa,
        visible_para_empresa=True,
        estado='pendiente'
    )

    # Marcar como vencidas las citas que ya pasaron su hora
    for cita in citas_pendientes:
        cita.marcar_vencida_si_paso()

    # Obtener todas las citas visibles para la empresa
    citas = Cita.objects.filter(
        empresa=empresa,
        visible_para_empresa=True
    )

    return render(request, 'app/empresa_panel.html', {
        'empresa': empresa,
        'citas': citas,
        'citas_pendientes_count': citas_pendientes.count(),

    })

def eliminar_cita_empresa(request, cita_id):
    """
    Marca la cita como no visible en el panel de la empresa en lugar de eliminarla de la base de datos.
    Solo permite “ocultar” si la cita ya está aceptada o rechazada.
    """
    if request.method == 'POST':
        empresa = get_object_or_404(Empresa, user=request.user)
        cita = get_object_or_404(Cita, id=cita_id, empresa=empresa)

        if cita.estado == 'pendiente':
            messages.error(request, 'No se puede eliminar una cita que aún está pendiente.')
            return redirect(reverse('app:empresa_panel'))
        
        #esto es para que no me permita borrar una cita aceptada , solo cuando este completada o vencida
        #if cita.estado == 'aceptada':
           # messages.error(request, 'No se puede eliminar una cita que aún está aceptada.')
            #return redirect(reverse('app:empresa_panel'))


        cita.visible_para_empresa = False
        cita.save()

        messages.success(request, 'La cita fue eliminada exitosamente del panel de la empresa.')
        return redirect(reverse('app:empresa_panel'))
    else:
        messages.error(request, 'Método no permitido.')
        return redirect(reverse('app:empresa_panel'))

    
# Asumo que tienes definida esta función y que lanza excepción si no puede enviar mensaje
# def enviar_mensaje_telegram(user, mensaje):
#     ...



import socket

# Generar código de 6 dígitos
def generar_codigo_6_digitos():
    return str(random.randint(100000, 999999))


# Solicitar recuperación de contraseña
def solicitar_recuperacion(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, '❌ No existe una cuenta con ese correo electrónico.')
            return redirect('app:solicitar_recuperacion')

        # Generar y guardar código
        codigo = generar_codigo_6_digitos()
        PasswordResetCode.objects.create(user=user, code=codigo)

        asunto = '🔐 Código de recuperación de contraseña'
        mensaje = f"""
🔐 ¡Hola {user.username}!

Hemos recibido una solicitud para restablecer tu contraseña.

Tu código de seguridad es: <strong>{codigo}</strong> ✅

⏳ Este código es válido por 15 minutos.

⚠️ Si tú no solicitaste este código, puedes ignorar este mensaje de forma segura.

Gracias por confiar en nosotros.
"""

        # También una versión sin HTML para el correo
        mensaje_plano = f"""
🔐 ¡Hola {user.username}!

Hemos recibido una solicitud para restablecer tu contraseña.

Tu código de seguridad es: {codigo} ✅

Este código es válido por 15 minutos.

⚠️ Si tú no solicitaste este código, puedes ignorar este mensaje de forma segura.

Gracias por confiar en nosotros.
"""

        enviado = False

        # Enviar por correo
        try:
            send_mail(
                asunto,
                mensaje_plano,  # solo texto plano
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            messages.success(request, '✅ Te hemos enviado un código de 6 dígitos al correo.')
            enviado = True
            request.session['recuperacion_user_id'] = user.id
        except (socket.timeout, socket.error):
            messages.warning(request, '⚠️ No se pudo enviar el correo por problemas de conexión. Intentando vía Telegram...')
        except Exception as e:
            messages.warning(request, f'⚠️ Error al enviar el correo: {str(e)}. Intentando vía Telegram...')

        # Enviar por Telegram si no se pudo por correo
        if not enviado:
            chat_id = None
            cliente = Cliente.objects.filter(user=user).first()
            empresa = Empresa.objects.filter(user=user).first()

            if cliente and cliente.telegram_chat_id:
                chat_id = str(cliente.telegram_chat_id)
            elif empresa and empresa.telegram_chat_id:
                chat_id = str(empresa.telegram_chat_id)

            if chat_id:
                try:
                    enviado = enviar_mensaje_telegram(chat_id, mensaje)
                    if enviado:
                        messages.success(request, '✅ Te hemos enviado el código por Telegram.')
                        request.session['recuperacion_user_id'] = user.id
                    else:
                        messages.error(request, '❌ Error al enviar el código por Telegram.')
                except Exception as e:
                    messages.error(request, f'❌ Error enviando a Telegram: {str(e)}')
            else:
                messages.error(request, '❌ Este usuario no tiene Telegram registrado.')

        # Si se envió correctamente
        if enviado:
            return redirect('app:ingresar_codigo')
        else:
            # Borra el código si no fue enviado para no dejar códigos inválidos en la DB
            PasswordResetCode.objects.filter(user=user, code=codigo).delete()
            return redirect('app:solicitar_recuperacion')

    return render(request, 'app/solicitar_recuperacion.html')


# Mostrar formulario para ingresar el código
def verificar_codigo(request):
    return render(request, 'app/ingresar_codigo.html')


# Restablecer la contraseña con código
def restablecer_contraseña_con_codigo(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo')
        nueva_password = request.POST.get('nueva_password')
        confirmar_password = request.POST.get('confirmar_password')

        if not codigo or not nueva_password or not confirmar_password:
            messages.error(request, '⚠️ Todos los campos son obligatorios.')
            return redirect('app:ingresar_codigo')

        if nueva_password != confirmar_password:
            messages.error(request, '❌ Las contraseñas no coinciden.')
            return redirect('app:ingresar_codigo')

        try:
            user_id = request.session.get('recuperacion_user_id')
            if not user_id:
                messages.error(request, '⚠️ Sesión expirada. Por favor, solicita el código de nuevo.')
                return redirect('app:solicitar_recuperacion')

            user = User.objects.get(id=user_id)
            reset_entry = PasswordResetCode.objects.filter(user=user, code=codigo).last()

            if not reset_entry or not reset_entry.is_valid():
                messages.error(request, '❌ Código inválido o expirado.')
                return redirect('app:ingresar_codigo')

            # Guardar nueva contraseña
            user.set_password(nueva_password)
            user.save()

            # Eliminar código usado
            reset_entry.delete()

            # Limpiar sesión
            if 'recuperacion_user_id' in request.session:
                del request.session['recuperacion_user_id']

            messages.success(request, '✅ Contraseña restablecida correctamente. Ya puedes iniciar sesión.')
            return redirect('app:login')

        except Exception as e:
            messages.error(request, f'Ocurrió un error: {str(e)}')
            return redirect('app:ingresar_codigo')

    return render(request, 'app/ingresar_codigo.html')

def obtener_servicios_por_empresa(request):
    """
    Endpoint para obtener servicios por ID de empresa.
    Devuelve los servicios activos con sus detalles: nombre, descripción, precio y duración,
    y el precio está formateado con coma para los miles.
    """
    empresa_id = request.GET.get('empresa_id')

    if not empresa_id:
        return JsonResponse({'message': 'Debe proporcionar un ID de empresa.'}, status=400)

    try:
        # Filtrar solo los servicios activos de la empresa
        servicios = Servicio.objects.filter(empresa_id=empresa_id, activo=True).values(
            'id', 'nombre', 'descripcion', 'precio', 'duracion'
        )

        if not servicios.exists():
            return JsonResponse({'message': 'No se encontraron servicios para esta empresa.'}, status=404)

        servicios_list = []
        for servicio in servicios:
            servicios_list.append({
                'id': servicio['id'],
                'nombre': servicio['nombre'],
                'descripcion': servicio['descripcion'] or 'Sin descripción',
                'precio': f"RD$ {formatear_con_coma_miles(servicio['precio'])}",
                'duracion': f"{servicio['duracion']} min" if servicio['duracion'] else "No especificado"
            })

        return JsonResponse({'servicios': servicios_list}, status=200)

    except Exception as e:
        return JsonResponse({'message': 'Error al procesar la solicitud.', 'error': str(e)}, status=500)

@requires_csrf_token
def csrf_failure(request, reason=""):
    return render(request, "csrf_failure.html", status=403)




 
 #revisar esto todavia no tiene funcion ver si se puede implementar , aqui quiero implementar editar empresa 
 # def actualizar_citas_automaticamente

 #poner tambien def panel cliente esto def panel_cliente(request):
   # actualizar_citas_automaticamente()
    # esto es para poner cuanto dura el servicios y la disponibilidad ...
    #editar_empresa.html app tambien
#disponibilidad


# desde aqui abajo arreglar

#logger = logging.getLogger(__name__)

#def enviar_recordatorio_cita(cita):
    """
    Envía un recordatorio de cita tanto al cliente como a la empresa
    por correo electrónico y, si está configurado, por Telegram.
    """
    mensaje_cliente = (
        f"Hola {cita.cliente.username},\n\n"
        f"Te recordamos que tienes una cita el día {cita.fecha.strftime('%d/%m/%Y')} a las {cita.hora.strftime('%H:%M')}.\n"
        "¡No olvides asistir!\n\n"
        "Saludos,\nTu equipo de Gestiona tu Cita."
    )

    mensaje_empresa = (
        f"Hola {cita.empresa.nombre_empresa},\n\n"
        f"Tienes una cita programada con {cita.cliente.username}.\n"
        f"Detalles de la cita:\n"
        f"- Fecha: {cita.fecha.strftime('%d/%m/%Y')}\n"
        f"- Hora: {cita.hora.strftime('%H:%M')}\n"
        f"- Servicio: {cita.servicio.nombre}\n\n"
        "Por favor, asegúrate de estar preparado para recibir al cliente.\n\n"
        "Saludos,\nTu equipo de Gestiona tu Cita."
    )

    # Enviar correo al cliente
    try:
        send_mail(
            'Recordatorio de cita',
            mensaje_cliente,
            settings.DEFAULT_FROM_EMAIL,
            [cita.cliente.email],
            fail_silently=False,
        )
        logger.info(f"Correo enviado al cliente {cita.cliente.username}.")
    except Exception as e:
        logger.error(f"Error al enviar correo al cliente {cita.cliente.username}: {e}")

    # Enviar mensaje de Telegram al cliente
    if cita.cliente.telegram_chat_id:
        try:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            async_to_sync(bot.send_message)(
                chat_id=cita.cliente.telegram_chat_id,
                text=mensaje_cliente
            )
            logger.info(f"Mensaje de Telegram enviado al cliente {cita.cliente.username}.")
        except Exception as e:
            logger.error(f"Error al enviar Telegram al cliente {cita.cliente.username}: {e}")

    # Enviar correo a la empresa
    try:
        send_mail(
            'Recordatorio de cita',
            mensaje_empresa,
            settings.DEFAULT_FROM_EMAIL,
            [cita.empresa.email_contacto],
            fail_silently=False,
        )
        logger.info(f"Correo enviado a la empresa {cita.empresa.nombre_empresa}.")
    except Exception as e:
        logger.error(f"Error al enviar correo a la empresa {cita.empresa.nombre_empresa}: {e}")

    # Enviar mensaje de Telegram a la empresa
    if cita.empresa.telegram_chat_id:
        try:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            async_to_sync(bot.send_message)(
                chat_id=cita.empresa.telegram_chat_id,
                text=mensaje_empresa
            )
            logger.info(f"Mensaje de Telegram enviado a la empresa {cita.empresa.nombre_empresa}.")
        except Exception as e:
            logger.error(f"Error al enviar Telegram a la empresa {cita.empresa.nombre_empresa}: {e}")


#def enviar_recordatorios_pendientes():


#borrar
#from django.http import JsonResponse
#from django.core.management import call_command
#from django.views.decorators.csrf import csrf_exempt

#@csrf_exempt
#def ejecutar_recordatorios(request):
    #if request.GET.get("token") != "secreto123":
       # return JsonResponse({"error": "No autorizado"}, status=401)

    #call_command("enviar_recordatorios")
   # return JsonResponse({"mensaje": "Recordatorios enviados"})
           #probar solamente

from django.db.models.functions import TruncMonth
from django.db.models import Sum


def formatear_con_coma_miles(valor):
    try:
        valor_int = int(round(valor))
        return f"{valor_int:,}".replace(",", ",")  # Si deseas punto en lugar de coma, cambia aquí
    except Exception:
        return valor

@login_required
def historial_citas_empresa(request):
    empresa = Empresa.objects.filter(user=request.user).first()
    if not empresa:
        return render(request, 'app/no_empresa.html')

    historial = Cita.objects.filter(empresa=empresa, servicio__isnull=False).order_by('-fecha', '-hora')

    ahora = datetime.now()

    for cita in historial:
        fecha_hora_cita = datetime.combine(cita.fecha, cita.hora)

        if cita.estado in ['pendiente', 'aceptada'] and fecha_hora_cita <= ahora:
            if cita.estado == 'aceptada':
                cita.estado = 'completada'
            elif cita.estado == 'pendiente':
                cita.estado = 'vencida'
            cita.save()

        # Total y formato de servicio
        precio = cita.servicio.precio if cita.servicio else 0
        cita.total_servicios = precio
        cita.total_servicios_formateado = formatear_con_coma_miles(precio)

        if cita.servicio:
            cita.servicio.precio_formateado = formatear_con_coma_miles(precio)

    # Resumen mensual de ingresos
    resumen_qs = (
        Cita.objects.filter(empresa=empresa, estado='completada', servicio__isnull=False)
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(total=Sum('servicio__precio'))
        .order_by('mes')
    )

    resumen_mensual = {}
    total_ingresos = 0
    ingreso_actual_mes = 0
    mes_actual = datetime.now().strftime('%b %Y')

    for item in resumen_qs:
        if item['mes']:
            mes_str = item['mes'].strftime('%b %Y')
            total_mes = float(item['total'] or 0)
            resumen_mensual[mes_str] = total_mes
            total_ingresos += total_mes
            if mes_str == mes_actual:
                ingreso_actual_mes = total_mes

    context = {
        'historial': historial,
        'total_ingresos': formatear_con_coma_miles(total_ingresos),
        'ingreso_actual_mes': formatear_con_coma_miles(ingreso_actual_mes),
        'mes_actual': mes_actual,
        'resumen_mensual_labels': list(resumen_mensual.keys()),
        'resumen_mensual_values': list(resumen_mensual.values()),
    }

    return render(request, 'app/historial_citas.html', context)
   # borrar sino funciona editar empresa


@login_required
def editar_empresa(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Verificar que el usuario autenticado es el dueño de la empresa
    if request.user != empresa.user:
        messages.error(request, "❌ No tienes permiso para editar esta empresa.")
        return redirect('app:empresa_panel')  # Asegúrate que esta URL exista

    if request.method == 'POST':
        form = EditarEmpresaForm(request.POST, instance=empresa, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Empresa actualizada correctamente.")
            return redirect('app:editar_empresa', empresa_id=empresa.id)
        else:
            messages.error(request, "❌ Por favor corrige los errores del formulario.")
    else:
        form = EditarEmpresaForm(instance=empresa, user=request.user)

    return render(request, 'editar_empresa.html', {'form': form})




@login_required
def subir_o_eliminar_foto_cliente(request):
    cliente = request.user.cliente

    if request.method == 'POST':
        if 'eliminar' in request.POST:
            # Eliminar foto
            if cliente.foto_perfil:
                cliente.foto_perfil.delete(save=True)
                messages.success(request, "✅ Foto eliminada correctamente.")
            else:
                messages.info(request, "No hay foto para eliminar.")
            return redirect('cliente_panel')  # Cambia si tienes otro nombre de vista

        elif request.FILES.get('foto'):
            # Subir o cambiar foto
            cliente.foto_perfil = request.FILES['foto']
            cliente.save()
            messages.success(request, "✅ Foto subida o actualizada correctamente.")
            return redirect('cliente_panel')

    return render(request, 'app/subir_foto.html')


#@login_required
#def subir_o_eliminar_logo_empresa(request):
    empresa = request.user.empresa

    if request.method == 'POST':
        if 'eliminar' in request.POST:
            # Eliminar logo
            if empresa.logo:
                empresa.logo.delete(save=True)
                messages.success(request, "✅ Logo eliminado correctamente.")
            else:
                messages.info(request, "No hay logo para eliminar.")
            return redirect('empresa_panel')  # Cambia si tienes otro nombre de vista

        elif request.FILES.get('foto'):
            # Subir o cambiar logo
            empresa.logo = request.FILES['foto']
            empresa.save()
            messages.success(request, "✅ Logo subido o actualizado correctamente.")
            return redirect('empresa_panel')

    return render(request, 'app/subir_logo.html')