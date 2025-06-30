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

# Configura Django para poder usar los modelos
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestiona_tu_cita.settings')  
django.setup()

from citas.models import Cliente, Empresa

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

TELEFONO = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "¡Hola! Para poder enviarte notificaciones, por favor envíame tu número telefónico con el que te registraste."
    )
    return TELEFONO

def enviar_mensaje_telegram(chat_id, mensaje):
    TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')
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
            logger.error(f"Error en respuesta Telegram: {result}")
    except Exception as e:
        logger.error(f"Error enviando mensaje Telegram: {e}")

async def recibir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        telefono = update.message.text.strip()
        chat_id = str(update.message.chat.id)
        telefono = telefono.replace(" ", "").replace("-", "").strip()
        logger.info(f"Teléfono recibido: {telefono}, Chat ID: {chat_id}")

        cliente_con_chat_id = await sync_to_async(lambda: Cliente.objects.filter(telegram_chat_id=chat_id).first())()
        empresa_con_chat_id = await sync_to_async(lambda: Empresa.objects.filter(telegram_chat_id=chat_id).first())()

        if cliente_con_chat_id or empresa_con_chat_id:
            await update.message.reply_text(
                "Este chat ya está registrado con un rol. Si necesitas cambiarlo, contacta soporte."
            )
            logger.warning(f"Chat ID {chat_id} ya registrado.")
            return ConversationHandler.END

        cliente = await sync_to_async(lambda: Cliente.objects.filter(telefono=telefono).first())()
        if cliente:
            cliente.telegram_chat_id = chat_id
            await sync_to_async(cliente.save)()
            await update.message.reply_text("¡Perfecto! Ahora recibirás notificaciones como cliente.")
            logger.info(f"Chat ID {chat_id} asociado como cliente.")
            return ConversationHandler.END

        empresa = await sync_to_async(lambda: Empresa.objects.filter(telefono=telefono).first())()
        if empresa:
            empresa.telegram_chat_id = chat_id
            await sync_to_async(empresa.save)()
            await update.message.reply_text("¡Perfecto! Ahora recibirás notificaciones como empresa.")
            logger.info(f"Chat ID {chat_id} asociado como empresa.")
            return ConversationHandler.END

        await update.message.reply_text(
            "No encontramos tu número en nuestra base de datos. Por favor verifica que te hayas registrado."
        )
        logger.warning(f"Teléfono {telefono} no encontrado en la base de datos.")
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error en recibir_telefono: {e}")
        await update.message.reply_text("Ocurrió un error, por favor intenta nuevamente.")
        return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Proceso cancelado.")
    return ConversationHandler.END

def main():
    TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN')

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TELEFONO: [MessageHandler(filters.TEXT & (~filters.COMMAND), recibir_telefono)],
        },
        fallbacks=[CommandHandler('cancel', cancelar)],
    )

    application.add_handler(conv_handler)

    logger.info("Bot iniciado. Esperando mensajes...")
    application.run_polling(poll_interval=1.0)

if __name__ == '__main__':
    main()
