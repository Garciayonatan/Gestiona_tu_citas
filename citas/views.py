
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import UserForm, ClienteForm, EmpresaForm, CitaForm
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

    # Obtener las citas del cliente y actualizar el estado si ya pasaron
    citas = Cita.objects.filter(cliente=cliente).select_related('empresa', 'servicio').order_by('fecha', 'hora')
    for cita in citas:
        cita.marcar_completada_si_paso()

    # Consultar las empresas y días laborables para mostrarlas en el panel
    empresas = Empresa.objects.prefetch_related('dias_laborables')
    dias = DiaLaborable.objects.all()

    # Renderizar el panel del cliente con las citas y empresas
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
        return redirect('app:cliente_panel')  # o un mensaje de error personalizado

    empresa = request.user.empresa
    citas = Cita.objects.filter(empresa=empresa).order_by('fecha', 'hora')
    dias_laborables = empresa.dias_laborables.all()
    servicios = Servicio.objects.filter(empresa=empresa)  # Agregado

    return render(request, 'app/empresa_panel.html', {
        'empresa': empresa,
        'citas': citas,
        'dias_laborables': dias_laborables,
        'servicios': servicios,  # Agregado
    })

#telegram noti
# Configurar el logger
# Configuración del logger
import logging
import requests
import json
from decouple import config
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.utils.decorators import method_decorator

from citas.models import Cliente, Empresa

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

# Función para enviar mensajes a Telegram
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

# Vista para recibir mensajes desde Telegram
@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    def post(self, request: HttpRequest):
        try:
            body = json.loads(request.body.decode('utf-8'))
            mensaje = body.get('message', {})
            texto = mensaje.get('text')
            chat_id = mensaje.get('chat', {}).get('id')

            logger.info(f"📩 Mensaje recibido: {texto} de chat_id: {chat_id}")

            # Si está esperando el número
            if chat_id in esperando_telefono:
                telefono = texto.strip()

                # Buscar si el teléfono existe en Cliente o Empresa
                cliente = Cliente.objects.filter(telefono=telefono).first()
                empresa = Empresa.objects.filter(telefono=telefono).first()

                if cliente:
                    cliente.telegram_chat_id = chat_id
                    cliente.save()
                    del esperando_telefono[chat_id]
                    enviar_mensaje_telegram(chat_id, "✅ Registro completado como <b>Cliente</b>. Recibirás notificaciones aquí.")
                elif empresa:
                    empresa.telegram_chat_id = chat_id
                    empresa.save()
                    del esperando_telefono[chat_id]
                    enviar_mensaje_telegram(chat_id, "✅ Registro completado como <b>Empresa</b>. Recibirás notificaciones aquí.")
                else:
                    enviar_mensaje_telegram(chat_id, "❌ Número no registrado. Intenta nuevamente o contacta soporte.")
                return JsonResponse({"ok": True})

            # Comando /start
            if texto == "/start":
                cliente = Cliente.objects.filter(telegram_chat_id=chat_id).first()
                empresa = Empresa.objects.filter(telegram_chat_id=chat_id).first()

                if cliente:
                    enviar_mensaje_telegram(chat_id, "👤 Hola <b>Cliente</b>. Recibirás notificaciones sobre tus citas aquí.")
                elif empresa:
                    enviar_mensaje_telegram(chat_id, "🏢 Hola <b>Empresa</b>. Recibirás notificaciones sobre tus clientes aquí.")
                else:
                    esperando_telefono[chat_id] = True
                    enviar_mensaje_telegram(chat_id, "📱 No estás registrado. Por favor, responde con el número de teléfono con el que te registraste.")
                return JsonResponse({"ok": True})

            return JsonResponse({"ok": True})

        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
            return JsonResponse({"error": str(e)}, status=500)

# Vista para enviar mensaje manualmente
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

        mensaje_empresa = (
            f"<html>\n"
            f"<body style=\"font-family: Arial, sans-serif; color: #333;\">\n"
            f"<h2 style=\"color: #0056b3;\">Actualización de Horario</h2>\n"
            f"<p>Hola <b>{empresa.nombre_dueno}</b>,</p>\n"
            f"<p>Te informamos que el horario de tu empresa <b>{nombre_empresa}</b> ha sido actualizado exitosamente. A continuación, te mostramos los nuevos detalles:</p>\n"
            f"<table style=\"border-collapse: collapse; margin: 20px 0;\">\n"
            f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Hora de inicio:</b></td><td style=\"padding: 8px; border: 1px solid #ddd;\">{hora_inicio.strftime('%H:%M')}</td></tr>\n"
            f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Hora de cierre:</b></td><td style=\"padding: 8px; border: 1px solid #ddd;\">{hora_cierre.strftime('%H:%M')}</td></tr>\n"
            f"</table>\n"
            f"<p>Gracias por confiar en nuestro sistema.</p>\n"
            f"<p style=\"color: #0056b3;\">El equipo de Gestiona tu Cita</p>\n"
            f"</body>\n"
            f"</html>"
        )

        mensaje_cliente = (
            f"<html>\n"
            f"<body style=\"font-family: Arial, sans-serif; color: #333;\">\n"
            f"<h2 style=\"color: #0056b3;\">Notificación de Cambio de Horario</h2>\n"
            f"<p>Hola,</p>\n"
            f"<p>Te informamos que la empresa <b>{nombre_empresa}</b> ha actualizado su horario de atención. A continuación, te mostramos los nuevos detalles:</p>\n"
            f"<table style=\"border-collapse: collapse; margin: 20px 0;\">\n"
            f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Hora de inicio:</b></td><td style=\"padding: 8px; border: 1px solid #ddd;\">{hora_inicio.strftime('%H:%M')}</td></tr>\n"
            f"<tr><td style=\"padding: 8px; border: 1px solid #ddd;\"><b>Hora de cierre:</b></td><td style=\"padding: 8px; border: 1px solid #ddd;\">{hora_cierre.strftime('%H:%M')}</td></tr>\n"
            f"</table>\n"
            f"<p>Esperamos que este cambio sea de tu conveniencia. Gracias por confiar en nosotros.</p>\n"
            f"<p style=\"color: #0056b3;\">El equipo de Gestiona tu Cita</p>\n"
            f"</body>\n"
            f"</html>"
        )

        mensaje_telegram = (
            f"🕒 La empresa {nombre_empresa} actualizó su horario:\n"
            f"{hora_inicio.strftime('%H:%M')} a {hora_cierre.strftime('%H:%M')}"
        )

        errores = []

        # Enviar correo a la empresa
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

        # Obtener clientes con citas pendientes o aceptadas
        clientes_con_citas = Cliente.objects.filter(
            citas__empresa=empresa,
            citas__estado__in=['pendiente', 'aceptada']
        ).distinct()

        for cliente in clientes_con_citas:
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
                    enviado = enviar_mensaje_telegram(cliente.telegram_chat_id, mensaje_cliente)
                    if not enviado:
                        errores.append(f"Telegram al cliente {cliente.id}")
                except Exception as e:
                    logger.error(f"Error al enviar Telegram al cliente {cliente.id}: {e}")
                    errores.append(f"Telegram al cliente {cliente.id}")

        # Enviar mensaje Telegram a la empresa
        if empresa.telegram_chat_id:
            try:
                enviado = enviar_mensaje_telegram(empresa.telegram_chat_id, mensaje_telegram)
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
                f"Hola {empresa.nombre_dueno},\n\n"
                f"Has actualizado los días laborables de tu empresa {empresa.nombre_empresa}.\n"
                f"Días seleccionados: {dias_lista}.\n\n"
                f"Gracias por gestionar tu negocio."
            )
            mensaje_cliente = (
                f"Hola,\n\n"
                f"La empresa {empresa.nombre_empresa} ha actualizado sus días laborables.\n"
                f"Nuevos días: {dias_lista}.\n\n"
                f"Gracias por confiar en nosotros."
            )
            mensaje_telegram = f"📅 {empresa.nombre_empresa} actualizó sus días laborables:\n{dias_lista}"

            errores = []

            # Enviar correo a la empresa
            try:
                send_mail(asunto, mensaje_empresa, settings.DEFAULT_FROM_EMAIL, [empresa.user.email])
            except Exception as e:
                logger.error(f"Error al enviar correo a la empresa: {e}")
                errores.append("correo a la empresa")

            # Enviar correos y mensajes Telegram a clientes con citas pendientes o aceptadas
            clientes_con_citas = Cliente.objects.filter(
                citas__empresa=empresa,
                citas__estado__in=['pendiente', 'aceptada']
            ).distinct()

            for cliente in clientes_con_citas:
                # Enviar correo al cliente
                if cliente.user.email:
                    try:
                        send_mail(asunto, mensaje_cliente, settings.DEFAULT_FROM_EMAIL, [cliente.user.email])
                    except Exception as e:
                        logger.error(f"Error al enviar correo al cliente {cliente.id}: {e}")
                        errores.append(f"correo al cliente {cliente.id}")

                # Enviar Telegram al cliente
                if cliente.telegram_chat_id:
                    try:
                        enviado = enviar_mensaje_telegram(cliente.telegram_chat_id, mensaje_cliente)
                        if not enviado:
                            errores.append(f"Telegram al cliente {cliente.id}")
                    except Exception as e:
                        logger.error(f"Error al enviar Telegram al cliente {cliente.id}: {e}")
                        errores.append(f"Telegram al cliente {cliente.id}")

            # Enviar mensaje Telegram a la empresa
            if empresa.telegram_chat_id:
                try:
                    enviado = enviar_mensaje_telegram(empresa.telegram_chat_id, mensaje_telegram)
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
        f"🕒 *Hora:* {cita.hora.strftime('%H:%M:%S')}\n"
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
        f"🕒 *Hora:* {cita.hora.strftime('%H:%M:%S')}\n"
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




# Vista para crear una nueva cita
logger = logging.getLogger(__name__)
@login_required(login_url='app:login')
def nueva_cita(request):
    cliente = get_object_or_404(Cliente, user=request.user)
    empresas = Empresa.objects.prefetch_related('dias_laborables')

    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            empresa_id = request.POST.get('empresa')
            servicio_id = request.POST.get('servicio')
            fecha_hora_str = request.POST.get('fecha_hora')
            comentarios = request.POST.get('comentarios', '')

            # Validar que los campos no estén vacíos
            if not (empresa_id and servicio_id and fecha_hora_str):
                messages.error(request, 'Todos los campos son obligatorios.')
                return redirect('app:nueva_cita')

            # Obtener empresa y servicio
            empresa = Empresa.objects.get(id=empresa_id)
            servicio = Servicio.objects.get(id=servicio_id, empresa=empresa)

            # Convertir fecha y hora
            fecha_hora_naive = datetime.strptime(fecha_hora_str, '%Y-%m-%dT%H:%M')
            fecha_hora = make_aware(fecha_hora_naive)

            # Validar que la fecha no sea en el pasado
            if fecha_hora < timezone.now():
                messages.error(request, 'No puedes agendar una cita en el pasado.')
                return redirect('app:nueva_cita')

            # Validar que el cliente no tenga una cita a la misma fecha y hora
            cita_existente = Cita.objects.filter(
                cliente=cliente,
                fecha=fecha_hora.date(),
                hora=fecha_hora.time(),
                estado__in=['pendiente', 'aceptada']
            ).exists()

            if cita_existente:
                messages.error(request, 'Ya tienes una cita pendiente o aceptada a esta fecha y hora.')
                return redirect('app:nueva_cita')

            # Validar que el día sea laborable
            dias_semana = ['lun', 'mar', 'mie', 'jue', 'vie', 'sab', 'dom']
            dia_codigo = dias_semana[fecha_hora.weekday()]
            dias_laborables = [d.lower() for d in empresa.dias_laborables.values_list('codigo', flat=True)]

            if dia_codigo not in dias_laborables:
                messages.error(request, 'La empresa no trabaja ese día.')
                return redirect('app:nueva_cita')

            # Validar que la hora esté dentro del horario laboral
            hora_cita = fecha_hora.time()
            if not (empresa.hora_inicio <= hora_cita <= empresa.hora_cierre):
                messages.error(request, 'La hora está fuera del horario laboral.')
                return redirect('app:nueva_cita')

            # Validar disponibilidad por capacidad
            fecha_hora_fin = fecha_hora + timedelta(minutes=servicio.duracion)
            citas_existentes = Cita.objects.filter(
                empresa=empresa,
                fecha=fecha_hora.date(),
                estado__in=['pendiente', 'aceptada']
            )

            citas_superpuestas = [
                cita for cita in citas_existentes
                if not (
                    timezone.make_aware(datetime.combine(cita.fecha, cita.hora)) + timedelta(minutes=cita.servicio.duracion) <= fecha_hora or
                    fecha_hora_fin <= timezone.make_aware(datetime.combine(cita.fecha, cita.hora))
                )
            ]

            if len(citas_superpuestas) >= empresa.capacidad:
                messages.error(request, 'No hay disponibilidad para la hora seleccionada. Intenta con otro horario.')
                return redirect('app:nueva_cita')

            # Crear la cita
            cita = Cita.objects.create(
                cliente=cliente,
                empresa=empresa,
                servicio=servicio,
                fecha=fecha_hora.date(),
                hora=hora_cita,
                comentarios=comentarios,
                estado='pendiente'
            )

            # Notificar al cliente y a la empresa
            asunto = f"📅 Nueva cita - {empresa.nombre_empresa}"
            mensaje_cliente = (
                f"Hola {cliente.nombre_completo},\n\n"
                f"Has solicitado una nueva cita:\n"
                f"🏢 Empresa: {empresa.nombre_empresa}\n"
                f"📜 Descripción: {servicio.descripcion}\n"
                f"🕒 Duración: {servicio.duracion} minutos\n"
                f"📅 Fecha: {cita.fecha}\n"
                f"🕒 Hora: {cita.hora.strftime('%H:%M')}\n"
                f"💼 Servicio: {servicio.nombre}\n"
                f"💰 Precio: {servicio.precio:.2f} DOP\n"
                f"📝 Comentarios: {comentarios}\n"
                f"📌 Estado: {cita.get_estado_display()}\n\n"
                f"Gracias por usar nuestro servicio."
            )
            mensaje_empresa = (
                f"Hola {empresa.nombre_dueno},\n\n"
                f"Se ha solicitado una nueva cita en tu empresa {empresa.nombre_empresa}:\n"
                f"👤 Cliente: {cliente.nombre_completo}\n"
                f"📜 Descripción del servicio: {servicio.descripcion}\n"
                f"🕒 Duración: {servicio.duracion} minutos\n"
                f"📅 Fecha: {cita.fecha}\n"
                f"🕒 Hora: {cita.hora.strftime('%H:%M')}\n"
                f"💼 Servicio: {servicio.nombre}\n"
                f"💰 Precio: {servicio.precio:.2f} DOP\n"
                f"📝 Comentarios: {comentarios}\n"
                f"📌 Estado: {cita.get_estado_display()}\n\n"
                f"Gracias por usar nuestro servicio."
            )

            try:
                send_mail(asunto, mensaje_cliente, settings.DEFAULT_FROM_EMAIL, [cliente.user.email])
                send_mail(asunto, mensaje_empresa, settings.DEFAULT_FROM_EMAIL, [empresa.user.email])
            except Exception as e:
                logger.warning(f"⚠️ Error al enviar correos: {e}")
                messages.warning(request, "Cita creada, pero ocurrió un error al enviar los correos.")

            try:
                if empresa.telegram_chat_id:
                    enviar_mensaje_telegram(empresa.telegram_chat_id, mensaje_empresa)
                if cliente.telegram_chat_id:
                    enviar_mensaje_telegram(cliente.telegram_chat_id, mensaje_cliente)
            except Exception as e:
                logger.warning(f"⚠️ Error al enviar Telegram: {e}")
                messages.warning(request, "Cita creada, pero no se pudo enviar mensaje por Telegram.")

            messages.success(request, "✅ Cita solicitada exitosamente.")
            return redirect('app:cliente_panel')

        except Empresa.DoesNotExist:
            messages.error(request, "Empresa no encontrada.")
        except Servicio.DoesNotExist:
            messages.error(request, "Servicio no válido o no pertenece a la empresa.")
        except ValueError as ve:
            messages.error(request, f"Fecha y hora inválidas: {ve}")
        except Exception as e:
            logger.error(f"❌ Error inesperado al crear cita: {e}", exc_info=True)
            messages.error(request, "❌ Ocurrió un error inesperado. Inténtalo más tarde.")

    return render(request, 'app/nueva_cita.html', {'empresas': empresas})




logger = logging.getLogger(__name__)

@login_required(login_url='app:login')
def editar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, cliente__user=request.user)

    # 🚫 Verificar si la cita ya está completada
    if cita.estado == 'completada':
        messages.error(request, "❌ No se puede editar una cita que ya está completada.")
        return redirect('app:cliente_panel')
    
    if cita.estado == 'rechazada':
        messages.error(request, "❌ No se puede editar una cita que ya está rechazada.")
        return redirect('app:cliente_panel')
    

    if request.method == 'POST':
        form = CitaForm(request.POST, instance=cita)
        if form.is_valid():
            cita_nueva = form.save(commit=False)
            servicio = cita_nueva.servicio

            # Calcular el rango de tiempo del nuevo horario
            fecha_hora_inicio = make_aware(datetime.combine(cita_nueva.fecha, cita_nueva.hora))
            fecha_hora_fin = fecha_hora_inicio + timedelta(minutes=servicio.duracion)

            # Verificar si el cliente ya tiene otra cita en otra empresa a la misma hora
            citas_cliente = Cita.objects.filter(
                cliente=cita_nueva.cliente,
                fecha=cita_nueva.fecha,
                estado__in=['pendiente', 'aceptada']
            ).exclude(id=cita.id)

            for otra_cita in citas_cliente:
                otra_inicio = make_aware(datetime.combine(otra_cita.fecha, otra_cita.hora))
                otra_fin = otra_inicio + timedelta(minutes=otra_cita.servicio.duracion)
                if fecha_hora_inicio < otra_fin and fecha_hora_fin > otra_inicio:
                    form.add_error(None, "❌ Ya tienes una cita en otra empresa en este horario.")
                    return render(request, 'app/editar_cita.html', {'form': form, 'cita': cita})

            # Buscar todas las citas aceptadas o pendientes que se crucen con la nueva
            citas_conflictivas = Cita.objects.filter(
                empresa=cita_nueva.empresa,
                fecha=cita_nueva.fecha,
                estado__in=['pendiente', 'aceptada']
            ).exclude(id=cita.id)

            conflictos = 0
            for otra in citas_conflictivas:
                otra_inicio = make_aware(datetime.combine(otra.fecha, otra.hora))
                otra_fin = otra_inicio + timedelta(minutes=otra.servicio.duracion)
                if fecha_hora_inicio < otra_fin and fecha_hora_fin > otra_inicio:
                    conflictos += 1

            if conflictos >= cita_nueva.empresa.capacidad:
                form.add_error(None, "❌ Ya hay otras citas que se cruzan con ese horario. Intenta con otro.")
                return render(request, 'app/editar_cita.html', {'form': form, 'cita': cita})

            cita_actualizada = form.save()

            notificar_cita(
                cita_actualizada,
                cita_nueva.cliente,
                cita_nueva.empresa,
                servicio,
                cita_nueva.comentarios,
                "actualizada"
            )

            messages.success(request, "✅ Cita actualizada correctamente.")
            return redirect('app:cliente_panel')
        else:
            messages.error(request, "❌ Por favor, corrige los errores en el formulario.")
    else:
        form = CitaForm(instance=cita)

    return render(request, 'app/editar_cita.html', {'form': form, 'cita': cita})


def notificar_cita(cita, cliente, empresa, servicio, comentarios, accion):
    asunto = f"Cita {accion.capitalize()} - {empresa.nombre_empresa}"
    mensajes = {
        "cliente": (
            f"Hola {cliente.nombre_completo},\n\n"
            f"Tu cita ha sido {accion}:\n"
            f"🏢 Empresa: {empresa.nombre_empresa}\n"
            f"📜 Descripción: {servicio.descripcion}\n"
            f"🕒 Duración: {servicio.duracion} minutos\n"
            f"💰 Precio: {servicio.precio:.2f} DOP\n"
            f"📅 Fecha: {cita.fecha}\n"
            f"🕒 Hora: {cita.hora.strftime('%H:%M')}\n"
            f"💼 Servicio: {servicio.nombre}\n"
            f"📝 Comentarios: {comentarios or 'Sin comentarios'}\n"
            f"📌 Estado: {cita.get_estado_display()}\n\n"
            f"Gracias por usar nuestro servicio."
        ),
        "empresa": (
            f"Hola {empresa.nombre_dueno},\n\n"
            f"Se ha actualizado una cita en tu empresa {empresa.nombre_empresa}:\n"
            f"👤 Cliente: {cliente.nombre_completo}\n"
            f"📜 Descripción: {servicio.descripcion}\n"
            f"🕒 Duración: {servicio.duracion} minutos\n"
            f"💰 Precio: {servicio.precio:.2f} DOP\n"
            f"📅 Fecha: {cita.fecha}\n"
            f"🕒 Hora: {cita.hora.strftime('%H:%M')}\n"
            f"💼 Servicio: {servicio.nombre}\n"
            f"📝 Comentarios: {comentarios or 'Sin comentarios'}\n"
            f"📌 Estado: {cita.get_estado_display()}\n\n"
            f"Gracias por usar nuestro servicio."
        )
    }

    try:
        if cliente.user.email:
            send_mail(asunto, mensajes["cliente"], settings.DEFAULT_FROM_EMAIL, [cliente.user.email])
        if empresa.user.email:
            send_mail(asunto, mensajes["empresa"], settings.DEFAULT_FROM_EMAIL, [empresa.user.email])
    except Exception as e:
        logger.error(f"Error al enviar correos: {e}")

    try:
        if cliente.telegram_chat_id:
            enviar_mensaje_telegram(cliente.telegram_chat_id, mensajes["cliente"])
        if empresa.telegram_chat_id:
            enviar_mensaje_telegram(empresa.telegram_chat_id, mensajes["empresa"])
    except Exception as e:
        logger.error(f"Error al enviar mensajes por Telegram: {e}")



@login_required(login_url='app:login')
def eliminar_cita(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id, cliente__user=request.user)

    if request.method == 'POST':
        # Guardar datos antes de eliminar
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

        # Eliminar la cita
        cita.delete()
        messages.success(request, '✅ Cita eliminada exitosamente.')

        # 🚫 Si estaba completada, no enviar notificaciones
        if estado == 'completada':
            return redirect('app:cliente_panel')

        if estado != 'rechazada':
            errores = []

            fecha_str = fecha.strftime('%d/%m/%Y')         # Muestra: 22/06/2025 (más amigable)
            hora_str = hora.strftime('%I:%M %p')           # Muestra: 08:01 PM


           # fecha_str = fecha.strftime('%Y-%m-%d')
            #hora_str = hora.strftime('%H:%M:%S')

            asunto_cliente = "📩 Confirmación de cancelación de cita"
            asunto_empresa = "📢 Notificación de cita cancelada por el cliente"

            # ✉️ Mensaje para el cliente
            mensaje_cliente = (
                f"Hola {cliente_nombre},\n\n"
                f"❌ Has cancelado tu cita con {empresa_nombre}.\n\n"
                f"👤 *Cliente:* {cliente_nombre}\n"
                f"🏢 *Empresa:* {empresa_nombre}\n"
                f"📅 *Fecha:* {fecha_str}\n"
                f"🕒 *Hora:* {hora_str}\n"
                f"📌 *Estado:* Cancelada\n\n"
                f"Gracias por usar nuestro sistema. 😊"
            )

            # ✉️ Mensaje para la empresa
            mensaje_empresa = (
                f"Hola {empresa_dueno},\n\n"
                f"❌ El cliente ha cancelado una cita.\n\n"
                f"👤 *Cliente:* {cliente_nombre}\n"
                f"🏢 *Empresa:* {empresa_nombre}\n"
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

            # Notificación visual
            if errores:
                messages.warning(request, f"⚠️ Cita eliminada, pero fallaron: {', '.join(errores)}")
            else:
                messages.success(request, "✉️ Notificaciones enviadas correctamente.")

        return redirect('app:cliente_panel')

    return render(request, 'app/eliminar_cita.html', {'cita': cita})


# servicios administrar 
@login_required
def administrar_servicios(request):
    """
    Vista para administrar los servicios de una empresa.
    Permite agregar, listar y eliminar servicios, así como actualizar la capacidad de empleados.
    """
    try:
        empresa = request.user.empresa
    except Empresa.DoesNotExist:
        return HttpResponseForbidden("No tienes una empresa asociada para gestionar servicios.")

    form = ServicioForm()
    empleados_rango = range(1, 101)  # Rango para seleccionar capacidad

    if request.method == 'POST':
        # Eliminar servicio
        if 'eliminar_servicio' in request.POST:
            servicio_id = request.POST.get('servicio_id')
            servicio = get_object_or_404(Servicio, id=servicio_id, empresa=empresa)
            servicio.delete()
            return redirect('app:servicios_empresa')

        # Actualizar capacidad (cantidad de empleados)
        elif 'cantidad_empleados' in request.POST:
            cantidad_empleados = request.POST.get('cantidad_empleados')
            if cantidad_empleados and cantidad_empleados.isdigit():
                empresa.cantidad_empleados = int(cantidad_empleados)
                empresa.save()
                return redirect('app:servicios_empresa')

        # Agregar nuevo servicio
        else:
            form = ServicioForm(request.POST)
            if form.is_valid():
                nuevo_servicio = form.save(commit=False)
                nuevo_servicio.empresa = empresa
                nuevo_servicio.save()
                return redirect('app:servicios_empresa')

    servicios = Servicio.objects.filter(empresa=empresa)

    return render(request, 'app/servicio_empresa.html', {
        'empresa': empresa,
        'form': form,
        'servicios': servicios,
        'empleados_rango': empleados_rango,
        'cantidad_empleados': empresa.cantidad_empleados,
    })
    
          #solicitar cita 

def solicitar_recuperacion(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'No existe una cuenta con ese correo electrónico.')
            return redirect('solicitar_recuperacion')

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        reset_path = reverse('restablecer_contraseña', kwargs={'codigo': f'{uid}-{token}'})
        reset_url = request.build_absolute_uri(reset_path)

        asunto = 'Restablecer tu contraseña'
        mensaje = render_to_string('citas/recuperacion_email.html', { #revisar
            'user': user,
            'reset_url': reset_url,
        })

        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        messages.success(request, 'Te hemos enviado un correo con las instrucciones para restablecer tu contraseña.')
        return redirect('solicitar_recuperacion')

    return render(request, 'citas/recuperar.html')

#cita eliminar empresa
# views.py

def empresa_panel(request):
    """
    Muestra el panel de la empresa, listando únicamente las citas
    cuya bandera visible_para_empresa esté en True.
    """
    empresa = get_object_or_404(Empresa, user=request.user)
    citas = Cita.objects.filter(empresa=empresa, visible_para_empresa=True)
    return render(request, 'app/empresa_panel.html', {
        'empresa': empresa,
        'citas': citas,
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

        cita.visible_para_empresa = False
        cita.save()

        messages.success(request, 'La cita fue eliminada exitosamente del panel de la empresa.')
        return redirect(reverse('app:empresa_panel'))
    else:
        messages.error(request, 'Método no permitido.')
        return redirect(reverse('app:empresa_panel'))

    

def solicitar_recuperacion(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            # Buscar usuario por correo
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            codigo = f"{uid}::{token}"

            asunto = 'Código para restablecer tu contraseña'
            mensaje = (
                f"Hola {user.username},\n\n"
                f"Para restablecer tu contraseña, usa este código:\n\n"
                f"{codigo}\n\n"
                "Ve a la página de restablecimiento y pega este código para cambiar tu contraseña.\n\n"
                "Si no solicitaste este correo, ignóralo."
            )

            # Intentar enviar por correo
            try:
                send_mail(
                    asunto,
                    mensaje,
                    'noreply@tusitio.com',  # Asegúrate de que este remitente esté autorizado por tu proveedor SMTP
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'Te hemos enviado un correo con el código para restablecer tu contraseña.')

            except (smtplib.SMTPException, socket.error, BadHeaderError):
                # Intentar enviar por Telegram si falla el correo
                try:
                    bot_token = settings.TELEGRAM_BOT_TOKEN
                    chat_id = settings.TELEGRAM_CHAT_ID
                    bot = Bot(token=bot_token)

                    mensaje_telegram = (
                        f"Hola {user.username},\n\n"
                        f"Tu código de recuperación es:\n\n"
                        f"{codigo}\n\n"
                        "Por favor, úsalo en la página de restablecimiento de contraseña."
                    )

                    # Llamar al método asíncrono usando async_to_sync
                    async_to_sync(bot.send_message)(chat_id=chat_id, text=mensaje_telegram)

                    messages.success(request, 'No pudimos enviarte un correo. Te hemos enviado el código de recuperación por Telegram.')

                except TelegramError as e:
                    messages.error(request, f'No se pudo enviar el mensaje por Telegram: {e}')

            return redirect('app:ingresar_codigo')

        except User.DoesNotExist:
            messages.error(request, 'No se encontró una cuenta con ese correo.')

        except Exception as e:
            messages.error(request, f'Ocurrió un error inesperado. Por favor, intenta más tarde: {str(e)}')

    return render(request, 'app/solicitar_recuperacion.html')

def ingresar_codigo(request):
    return render(request, 'app/ingresar_codigo.html')


def restablecer_contraseña_con_codigo(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo')
        nueva_password = request.POST.get('nueva_password')
        confirmar_password = request.POST.get('confirmar_password')

        if not codigo:
            messages.error(request, '⚠️ Debes ingresar el código que te enviamos por correo.')
            return redirect('app:restablecer_contraseña')  # Se puede redirigir a la misma vista

        if not nueva_password or not confirmar_password:
            messages.error(request, '⚠️ Debes ingresar y confirmar tu nueva contraseña.')
            return redirect('app:restablecer_contraseña')

        if nueva_password != confirmar_password:
            messages.error(request, '❌ Las contraseñas no coinciden.')
            return redirect('app:restablecer_contraseña')

        try:
            uidb64, token = codigo.split('::')
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(nueva_password)
            user.save()
            messages.success(request, '✅ ¡Contraseña restablecida correctamente! Ahora puedes iniciar sesión.')
            return redirect('app:login')
        else:
            messages.error(request, '❌ El código es inválido o ha expirado.')
            return redirect('app:restablecer_contraseña')

    # Si es GET, muestra el formulario ingresar_codigo.html
    return render(request, 'app/ingresar_codigo.html')

    # Mostrar formulario de restablecer contraseña con código
    return render(request, 'app/restablecer_contraseña.html')

def obtener_servicios_por_empresa(request):
    """
    Endpoint para obtener servicios por ID de empresa.
    Devuelve los servicios con sus detalles: nombre, descripción, precio y duración.
    """
    empresa_id = request.GET.get('empresa_id')
    
    if not empresa_id:
        return JsonResponse({'message': 'Debe proporcionar un ID de empresa.'}, status=400)

    try:
        servicios = Servicio.objects.filter(empresa_id=empresa_id).values(
            'id', 'nombre', 'descripcion', 'precio', 'duracion'
        )

        if not servicios.exists():
            return JsonResponse({'message': 'No se encontraron servicios para esta empresa.'}, status=404)

        return JsonResponse({'servicios': list(servicios)}, status=200)
    except Exception as e:
        # Manejo de errores generales para prevenir fallos inesperados
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



    """
    Envía recordatorios para todas las citas aceptadas que cumplen
    con las condiciones de tiempo para los recordatorios configurados.
    """
    ahora = now()
    citas = Cita.objects.filter(fecha__gte=ahora.date(), estado="aceptada").exclude(
        fecha=ahora.date(), hora__lt=ahora.time()
    )

    for cita in citas:
        fecha_hora_cita = make_aware(datetime.combine(cita.fecha, cita.hora))
        minutos_para_cita = (fecha_hora_cita - ahora).total_seconds() / 60

        logger.info(f"Procesando cita ID {cita.id} - Minutos para la cita: {minutos_para_cita:.2f}")

        # Primer recordatorio: 15 minutos antes
        if not cita.primer_recordatorio_enviado and 0 <= minutos_para_cita <= 15:
            enviar_recordatorio_cita(cita)
            cita.primer_recordatorio_enviado = True
            cita.save()
            logger.info(f"Primer recordatorio enviado para la cita ID {cita.id}.")

        # Segundo recordatorio: 10 minutos antes
        if not cita.segundo_recordatorio_enviado and 0 <= minutos_para_cita <= 10:
            enviar_recordatorio_cita(cita)
            cita.segundo_recordatorio_enviado = True
            cita.save()
            logger.info(f"Segundo recordatorio enviado para la cita ID {cita.id}.")


            