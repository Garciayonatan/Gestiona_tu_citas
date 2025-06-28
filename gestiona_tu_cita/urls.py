from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views  # Importar vistas predeterminadas de autenticación

urlpatterns = [
    path('admin/', admin.site.urls),  # Ruta para la administración de Django

    # Incluye las rutas de tu app con un namespace 'app'
    path('', include(('citas.urls', 'app'), namespace='app')),

    # Ruta para login usando las vistas predeterminadas de Django
    path('accounts/login/', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
]
