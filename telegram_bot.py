import os
import django
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from asgiref.sync import sync_to_async
from decouple import config

# Configura Django para acceder a modelos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestiona_tu_cita.settings')
django.setup()

from citas.models import Cliente, Empresa

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Constante para la conversación
TELEFONO = 1

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "¡Hola! Para poder enviarte notificaciones, por favor envíame tu número telefónico con el que te registraste."
    )
    return TELEFONO

# Función para enviar mensajes desde Django
def enviar_mensaje_telegram(chat_id, mensaje):
    try:
        TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("Token de Telegram vacío.")
    except Exception as e:
        logger.error(f"❌ TOKEN de Telegram no disponible: {e}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            logger.error(f"❌ Error en la respuesta de Telegram: {result}")
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")

# Función para recibir número y registrar chat_id
async def recibir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    telefono = update.message.text.strip().replace(" ", "").replace("-", "")
    chat_id = str(update.message.chat.id)
    logger.info(f"📥 Teléfono recibido: {telefono} - Chat ID: {chat_id}")

    cliente_chat = await sync_to_async(Cliente.objects.filter(telegram_chat_id=chat_id).first)()
    empresa_chat = await sync_to_async(Empresa.objects.filter(telegram_chat_id=chat_id).first)()

    if cliente_chat or empresa_chat:
        await update.message.reply_text(
            "Este chat ya está registrado con un rol. Si necesitas cambiarlo, contacta soporte."
        )
        logger.warning(f"⚠️ Chat ID {chat_id} ya estaba registrado.")
        return ConversationHandler.END

    cliente = await sync_to_async(Cliente.objects.filter(telefono=telefono).first)()
    if cliente:
        cliente.telegram_chat_id = chat_id
        await sync_to_async(cliente.save)()
        await update.message.reply_text("✅ ¡Perfecto! Ahora recibirás notificaciones como cliente.")
        logger.info(f"✅ Chat ID {chat_id} registrado como cliente.")
        return ConversationHandler.END

    empresa = await sync_to_async(Empresa.objects.filter(telefono=telefono).first)()
    if empresa:
        empresa.telegram_chat_id = chat_id
        await sync_to_async(empresa.save)()
        await update.message.reply_text("✅ ¡Perfecto! Ahora recibirás notificaciones como empresa.")
        logger.info(f"✅ Chat ID {chat_id} registrado como empresa.")
        return ConversationHandler.END

    await update.message.reply_text(
        "❌ No encontramos tu número en la base de datos. Verifica que estés registrado."
    )
    logger.warning(f"❌ Número {telefono} no encontrado.")
    return ConversationHandler.END

# Comando /cancel
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Proceso cancelado.")
    return ConversationHandler.END

# Ejecutar bot
def main():
    try:
        TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("Token no definido.")
    except Exception as e:
        logger.error(f"❌ Error cargando TELEGRAM_BOT_TOKEN: {e}")
        return

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TELEFONO: [MessageHandler(filters.TEXT & (~filters.COMMAND), recibir_telefono)],
        },
        fallbacks=[CommandHandler('cancel', cancelar)],
    )

    application.add_handler(conv_handler)
    logger.info("🤖 Bot iniciado. Esperando mensajes...")
    application.run_polling()

if __name__ == '__main__':
    main()
