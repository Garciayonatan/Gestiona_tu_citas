import logging
from twilio.rest import Client
from django.conf import settings

logger = logging.getLogger(__name__)

def formatear_numero(numero: str) -> str | None:
    """
    Formatea el número de teléfono al formato internacional con prefijo +1 para RD.
    Ejemplos válidos:
      - 8091234567 → +18091234567
      - 18091234567 → +18091234567
      - +18091234567 → +18091234567
    """
    if not numero:
        return None

    numero = numero.strip().replace(" ", "").replace("-", "")

    if numero.startswith("+"):
        return numero
    if numero.startswith("1") and len(numero) == 11:
        return f"+{numero}"
    if numero.startswith(("809", "829", "849")) and len(numero) == 10:
        return f"+1{numero}"

    logger.warning(f"❌ Número inválido: {numero}")
    return None

def enviar_whatsapp(numero_destino: str, mensaje: str) -> bool:
    """
    Envía un mensaje de WhatsApp usando Twilio a un número formateado.
    """
    numero_formateado = formatear_numero(numero_destino)
    if not numero_formateado:
        logger.warning(f"❌ No se pudo enviar WhatsApp: número no válido -> {numero_destino}")
        return False

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        mensaje_enviado = client.messages.create(
            body=mensaje,
            from_=f'whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}',
            to=f'whatsapp:{numero_formateado}'
        )
        logger.info(f"✅ WhatsApp enviado a {numero_formateado}, SID: {mensaje_enviado.sid}, Estado: {mensaje_enviado.status}")
        return True

    except Exception as e:
        logger.warning(f"⚠️ Error al enviar WhatsApp a {numero_formateado}: {e}", exc_info=True)
        return False
