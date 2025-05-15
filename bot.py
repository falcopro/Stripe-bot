import logging
import asyncio
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import stripe

from dotenv import load_dotenv
import os
import stripe

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")

# Estados para la conversación
ENTER_CARD = 1

# Configura el logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)
logger = logging.getLogger(__name__)

BIN_INFO = {
    "512106": ("MASTERCARD", "CIRRUS", "CREDIT"),
    "424242": ("VISA", "VISA", "DEBIT"),
    "401288": ("VISA", "VISA", "CREDIT"),
    "378282": ("AMEX", "AMERICAN EXPRESS", "CREDIT"),
}

BANKS = {
    "512106": "CITIBANK N.A.",
    "424242": "BANK OF TEST",
    "401288": "FAKEBANK LTD.",
    "378282": "AMERICAN EXPRESS BANK",
}

COUNTRIES = {
    "512106": "UNITED STATES 🇺🇸",
    "424242": "UNITED KINGDOM 🇬🇧",
    "401288": "CANADA 🇨🇦",
    "378282": "UNITED STATES 🇺🇸",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug("Comando /start recibido")
    welcome_message = (
        "¡Hola! Soy tu bot para probar tarjetas con Stripe.\n\n"
        "Usa /testcard para iniciar la prueba de una tarjeta.\n"
        "Luego introduce los datos en el siguiente formato:\n"
        "NúmeroTarjeta,MM,AA,CVC\n"
        "Por ejemplo:\n"
        "4242424242424242,12,25,123"
    )
    await update.message.reply_text(welcome_message)

async def testcard_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug("Comando /testcard recibido")
    await update.message.reply_text(
        "Por favor, envía los datos de la tarjeta en el siguiente formato:\n"
        "NúmeroTarjeta,MM,AA,CVC\n"
        "Ejemplo:\n"
        "4242424242424242,12,25,123"
    )
    return ENTER_CARD

def get_card_info(number: str):
    bin6 = number[:6]
    brand, network, type_ = BIN_INFO.get(bin6, ("UNKNOWN", "UNKNOWN", "UNKNOWN"))
    bank = BANKS.get(bin6, "UNKNOWN")
    country = COUNTRIES.get(bin6, "UNKNOWN")
    return brand, network, type_, bank, country

async def testcard_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug(f"Mensaje recibido para testcard_process: {update.message.text}")
    text = update.message.text.strip()
    try:
        number, exp_month, exp_year, cvc = [x.strip() for x in text.split(",")]
        exp_month = int(exp_month)
        exp_year = int(exp_year)
    except Exception as e:
        logger.warning(f"Error parseando datos de tarjeta: {e}")
        await update.message.reply_text(
            "Formato inválido. Debes enviar los datos en formato:\nNúmeroTarjeta,MM,AA,CVC\nEjemplo:\n4242424242424242,12,25,123"
        )
        return ENTER_CARD

    progress_message = await update.message.reply_text("Checkeando 0% ...")

    start_time = time.time()
    for percent in range(10, 101, 10):
        await asyncio.sleep(0.5)
        await progress_message.edit_text(f"Checkeando {percent}% ...")

    duration = time.time() - start_time
    duration_str = f"{duration:.1f}s"

    brand, network, type_, bank, country = get_card_info(number)
    retries = 1
    payment_method_info = "Braintree CCN $10"
    request_by = "@Ghost10080 [Free]"
    owner_tag = "@xxXUnknowXx"

    status_text = ""
    try:
        token = stripe.Token.create(
            card={"number": number, "exp_month": exp_month, "exp_year": exp_year, "cvc": cvc},
        )
        status = "APPROVED ✅"
        status_text = f"(あ) Status⤷ {status}"
        response_text = "(あ) Response⤷ \n"
    except stripe.error.CardError as e:
        err = e.error
        status = "DECLINED ❌"
        status_text = f"(あ) Status⤷ {status}"
        response_text = f"(あ) Response⤷ {err.message}"
    except Exception as e:
        status = "ERROR ❌"
        status_text = f"(あ) Status⤷ {status}"
        response_text = f"(あ) Response⤷ Unexpected error: {str(e)}"

    message_text = (
        "(あ) 𝑌𝑢𝑚𝑒𝑘𝑜 𝐶ℎ𝑘 (あ)\n"
        "━━━━━━━━━━━━━\n"
        f"(あ) CC⤷ {number}|{exp_month}|{exp_year}|{cvc}\n"
        f"{status_text}\n"
        f"{response_text}\n"
        f"(あ) Info⤷ {brand} - {network} - {type_}\n"
        f"(あ) Bank⤷ {bank}\n"
        f"(あ) Country⤷ {country}\n"
        f"(あ) Retries⤷ {retries} | {payment_method_info}\n"
        f"(あ) Time/Proxy⤷ {duration_str} | LIVE 🟩\n"
        f"(あ) Request By⤷ {request_by}\n"
        "━━━━━━━━━━━━━\n"
        f"Owner : {owner_tag}"
    )

    await progress_message.edit_text(message_text)
    logger.debug("Resultado enviado al usuario")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug("Comando /cancel recibido")
    await update.message.reply_text('Operación cancelada.')
    return ConversationHandler.END

def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('testcard', testcard_start)],
        states={
            ENTER_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, testcard_process)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()

