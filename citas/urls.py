from django.urls import path
from . import views
from .views import obtener_servicios_por_empresa 
from .views import EnviarMensajeTelegramView
#from citas.views import webhook_telegram
from citas.views import TelegramWebhookView
from .views import ejecutar_recordatorios 


app_name = 'app'

urlpatterns = [
    # Autenticación

    path('', views.home, name='inicio'),           # Página principal (home) al entrar en /
    path('login/', views.login_view, name='login'),    # Página de login en /login/
    path('logout/', views.logout_view, name='logout'), # Logout en /logout/
    path('home/', views.home, name='home'),         # También accesible en /home/

    # original
   #path('', views.login_view, name='login'),                      # Página de inicio de sesión
   #path('logout/', views.logout_view, name='logout'),             # Cerrar sesión

  # path('telegram-webhook/', webhook_telegram, name='telegram_webhook'),
   # path('enviar-mensaje-telegram/', EnviarMensajeTelegramView.as_view(), name='enviar_mensaje_telegram'),

   path('enviar-mensaje-telegram/', EnviarMensajeTelegramView.as_view(), name='enviar_mensaje_telegram'),

   path('telegram-webhook/', TelegramWebhookView.as_view(), name='telegram_webhook'),
   

    # Página principal después del inicio de sesión
    #path('', views.home, name='inicio'),  # ← Ruta raíz que carga home.html
   # path('home/', views.home, name='home'),

    # Registro de usuarios
    path('register/cliente/', views.registro_cliente, name='register_cliente'),
    path('register/empresa/', views.registro_empresa, name='register_empresa'),

    # Paneles de usuario
    path('cliente/panel/', views.cliente_panel, name='cliente_panel'),        # Panel del cliente
    path('empresa/panel/', views.empresa_panel, name='empresa_panel'),        # Panel de la empresa

    # Gestión de citas
    path('cita/nueva/', views.nueva_cita, name='nueva_cita'),                                 # Crear nueva cita
    path('cita/aceptar/<int:cita_id>/', views.aceptar_cita, name='aceptar_cita'),             # Aceptar una cita
    path('cita/rechazar/<int:cita_id>/', views.rechazar_cita, name='rechazar_cita'),          # Rechazar una cita
    path('cita/editar/<int:cita_id>/', views.editar_cita, name='editar_cita'),                # Editar una cita
    path('cita/eliminar/<int:cita_id>/', views.eliminar_cita, name='eliminar_cita'),          # Eliminar una cita
    path('cita/<int:cita_id>/cancelar/', views.cancelar_cita, name='cancelar_cita'),          # Cancelar una cita
    path('empresa/cita/eliminar/<int:cita_id>/', views.eliminar_cita_empresa, name='eliminar_cita_empresa'),

    # Gestión del horario y días laborables de la empresa
    path('empresa/editar-horario/', views.editar_horario, name='editar_horario'),            # Editar horario de trabajo
    path('empresa/editar-dias/', views.editar_dias_laborables, name='editar_dias_laborables'), # Editar días laborables

    # Recuperación de contraseña
    path('ingresar-codigo/', views.ingresar_codigo, name='ingresar_codigo'),
    path('recuperar/', views.solicitar_recuperacion, name='solicitar_recuperacion'),
    path('restablecer-contrasena/', views.restablecer_contraseña_con_codigo, name='restablecer_contraseña'),
    #path('empresa/servicios/', views.administrar_servicios, name='servicios_empresa'),

    
     #funciona con este el panel de la empresa

     path('empresa/servicios/', views.administrar_servicios, name='servicios_empresa'),

     #path('cargar-servicios/', views.cargar_servicios, name='cargar_servicios'),

     #path('api/servicios/', views.cargar_servicios, name='cargar_servicios'),
     path('api/servicios/', obtener_servicios_por_empresa, name='api_servicios'),

   
     #path('ejecutar-recordatorios/', ejecutar_recordatorios, name='ejecutar_recordatorios'),
     #usar
      path('ejecutar-recordatorios/', ejecutar_recordatorios, name='ejecutar_recordatorios'),
     
     #usar
        

     
     
     #revisar 
   





    #path('empresa/servicios/', views.administrar_servicios, name='administrar_servicios'),

     #path('empresa/servicios/', views.servicios_empresa, name='servicios_empresa')


]


