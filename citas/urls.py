from django.urls import path
from . import views
from .views import obtener_servicios_por_empresa, EnviarMensajeTelegramView
from citas.views import TelegramWebhookView

#borrar solo estoy probando
from .views import historial_citas_empresa


app_name = 'app'

urlpatterns = [
    # Autenticación
    path('', views.home, name='inicio'),                          # Página principal
    path('login/', views.login_view, name='login'),               # Login
    path('logout/', views.logout_view, name='logout'),            # Logout
    path('home/', views.home, name='home'),                        # Home alternativa

    # Telegram
    path('enviar-mensaje-telegram/', EnviarMensajeTelegramView.as_view(), name='enviar_mensaje_telegram'),
    path('telegram-webhook/', TelegramWebhookView.as_view(), name='telegram_webhook'),

    # Registro de usuarios
    path('register/cliente/', views.registro_cliente, name='register_cliente'),
    path('register/empresa/', views.registro_empresa, name='register_empresa'),

    # Paneles de usuario
    path('cliente/panel/', views.cliente_panel, name='cliente_panel'),
    path('empresa/panel/', views.empresa_panel, name='empresa_panel'),
    #path('empresa/panel/', views.redirigir_panel_empresa, name='redirigir_panel_empresa'), #dirigir


    path('empresa/<int:empresa_id>/editar/', views.editar_empresa, name='editar_empresa'),

    # Gestión de citas
    path('cita/nueva/', views.nueva_cita, name='nueva_cita'),
    path('cita/aceptar/<int:cita_id>/', views.aceptar_cita, name='aceptar_cita'),
    path('cita/rechazar/<int:cita_id>/', views.rechazar_cita, name='rechazar_cita'),
    path('cita/editar/<int:cita_id>/', views.editar_cita, name='editar_cita'),
    path('cita/eliminar/<int:cita_id>/', views.eliminar_cita, name='eliminar_cita'),
    path('cita/<int:cita_id>/cancelar/', views.cancelar_cita, name='cancelar_cita'),
    path('empresa/cita/eliminar/<int:cita_id>/', views.eliminar_cita_empresa, name='eliminar_cita_empresa'),

    # Gestión del horario y días laborables de la empresa
    path('empresa/editar-horario/', views.editar_horario, name='editar_horario'),
    path('empresa/editar-dias/', views.editar_dias_laborables, name='editar_dias_laborables'),

    # Recuperación de contraseña
    path('recuperar/', views.solicitar_recuperacion, name='solicitar_recuperacion'),
    path('ingresar-codigo/', views.verificar_codigo, name='ingresar_codigo'),  # corregido, evita error
    path('restablecer-contrasena/', views.restablecer_contraseña_con_codigo, name='restablecer_contraseña'),

    # Panel empresa - servicios
     path('empresa/servicios/', views.administrar_servicios, name='servicios_empresa'),

    # API servicios
    path('api/servicios/', obtener_servicios_por_empresa, name='api_servicios'),

#''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

                 #'''''''                                                                         #borrar
      #borrar esto hoy 10 del 7 
    path('empresa/historial-citas/', historial_citas_empresa, name='historial_citas_empresa'),
    
    #servicios editar

   path('servicio/editar/<int:servicio_id>/', views.editar_servicio, name='editar_servicio'),
   #path('empresa/<int:empresa_id>/servicios/', views.servicios_empresa, name='servicios_empresa'),

    #borrar si no quiero esto de historial

    #-----------------------------------------------------------activar cuando yo quiera
    #path('cliente/subir-foto/', views.subir_o_eliminar_foto_cliente, name='subir_foto_cliente'),
    #path('empresa/subir-logo/', views.subir_o_eliminar_logo_empresa, name='subir_logo_empresa'),
    #este tambien activar cuando yo quiera foto empresa y cliente
]





    #path('empresa/servicios/', views.administrar_servicios, name='administrar_servicios'),

     #path('empresa/servicios/', views.servicios_empresa, name='servicios_empresa')





