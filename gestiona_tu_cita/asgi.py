
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestiona_tu_cita.settings')

application = get_asgi_application()
        