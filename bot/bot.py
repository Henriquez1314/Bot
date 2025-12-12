import requests
import random
import time
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters, CallbackQueryHandler
)
from dotenv import load_dotenv

# ==========================
# Cargar .env
# ==========================
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL")

# ==========================
# Estados de conversación
# ==========================
ESPERANDO_NEGOCIO, ESPERANDO_CAPTCHA, ESPERANDO_DIRECCION, ESPERANDO_TELEFONO = range(4)

# ==========================
# Datos
# ==========================
carritos = {}
usuarios_negocio = {}
historial_pedidos = {}
captcha_pendiente = {}
captcha_modo = {}

# ==========================
# Funciones anti-spam
# ==========================
def registrar_pedido(uid: int):
    ahora = time.time()
    historial_pedidos.setdefault(uid, [])
    historial_pedidos[uid].append(ahora)
    historial_pedidos[uid] = [t for t in historial_pedidos[uid] if ahora - t < 600]

def necesita_captcha(uid: int):
    return uid in historial_pedidos and len(historial_pedidos[uid]) >= 5

async def pedir_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    resultado = a + b
    captcha_pendiente[uid] = {"resultado": resultado}
    captcha_modo[uid] = True

    await update.effective_message.reply_text(
        f"🔒 *Seguridad anti-spam*\n\n"
        f"Has hecho varios pedidos en poco tiempo.\n"
        f"Resuelve este captcha para continuar:\n\n"
        f"➡ ¿Cuánto es *{a} + {b}*?",
        parse_mode="Markdown"
    )
    return ESPERANDO_CAPTCHA

async def validar_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    texto = update.effective_message.text

    if not texto.isdigit():
        await update.effective_message.reply_text("❌ Debes responder con un número. Intenta de nuevo.")
        return ESPERANDO_CAPTCHA

    if int(texto) != captcha_pendiente[uid]["resultado"]:
        await update.effective_message.reply_text("❌ Captcha incorrecto. Intenta otra vez.")
        return ESPERANDO_CAPTCHA

    captcha_modo[uid] = False
    await update.effective_message.reply_text("🔓 Captcha correcto. Continuemos.")
    await update.effective_message.reply_text("📍 Envíame tu dirección completa:")
    return ESPERANDO_DIRECCION

# ==========================
# /start — elegir negocio
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = requests.get(f"{API_URL}/negocios", timeout=10)
        negocios = r.json()
    except:
        await update.effective_message.reply_text("❌ Error obteniendo negocios.")
        return ESPERANDO_NEGOCIO

    if not negocios:
        await update.effective_message.reply_text("No hay negocios disponibles.")
        return ESPERANDO_NEGOCIO

    botones = [[InlineKeyboardButton(n["Nombre"], callback_data=str(n["Id"]))] for n in negocios]
    markup = InlineKeyboardMarkup(botones)

    await update.effective_message.reply_text(
        "👋 *Bienvenido al Bot E-Commerce*\n\n"
        "Selecciona un negocio para comenzar:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    return ESPERANDO_NEGOCIO

async def recibir_negocio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    message = update.effective_message

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        business_id = int(query.data)
    else:
        try:
            business_id = int(message.text)
        except ValueError:
            await message.reply_text("Por favor, ingresa un número válido.")
            return ESPERANDO_NEGOCIO

    try:
        r = requests.get(f"{API_URL}/negocio/{business_id}", timeout=10)
        if r.status_code != 200:
            await message.reply_text("❌ Ese negocio no existe. Intenta nuevamente.")
            return ESPERANDO_NEGOCIO
        data = r.json()
        nombre_negocio = data["Nombre"]
        usuarios_negocio[uid] = business_id

        await message.reply_text(
            f"✅ Negocio *{nombre_negocio}* seleccionado.\n\n"
            "📌 Comandos útiles:\n"
            "• /productos – Ver catálogo\n"
            "• /carrito – Ver tu carrito\n"
            "• /confirmar – Confirmar pedido\n"
            "• /mispedidos – Ver tus pedidos\n"
            "• /cancelar – Vaciar carrito\n\n"
            "Si deseas cambiar de negocio, usa /start.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error obteniendo negocio: {str(e)}")
        return ESPERANDO_NEGOCIO

    return ConversationHandler.END

# ==========================
# /productos
# ==========================
async def productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    business_id = usuarios_negocio.get(uid)

    if not business_id:
        await update.effective_message.reply_text("❌ Primero selecciona un negocio usando /start.")
        return

    try:
        res = requests.get(f"{API_URL}/productos?business_id={business_id}", timeout=10)
        prods = res.json()
    except:
        await update.effective_message.reply_text("❌ Error conectando con la API.")
        return

    if not prods:
        await update.effective_message.reply_text("No hay productos disponibles.")
        return

    await update.effective_message.reply_text(
        "🛍️ *Catálogo disponible*\n\n"
        "📌 Recuerda:\n"
        "• /agregar ID CANTIDAD – Añadir productos\n"
        "• /carrito – Ver tu carrito\n"
        "• /confirmar – Finalizar pedido\n"
        "• /mispedidos – Ver tus pedidos\n"
        "• /cancelar – Vaciar carrito\n"
        "• /start – Cambiar de negocio",
        parse_mode="Markdown"
    )

    for p in prods:
        texto = (
            f"🆔 *ID:* {p['Id']}\n"
            f"📦 *{p['Nombre']}*\n"
            f"💲 Precio: ${p['Precio']}\n"
            f"📃 {p.get('DescripcionCorta','')}\n\n"
            f"Para agregar:\n"
            f"`/agregar {p['Id']} 1`"
        )
        if p.get("ImagenUrl"):
            await update.effective_message.reply_photo(photo=p["ImagenUrl"], caption=texto, parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(texto, parse_mode="Markdown")

# ==========================
# /agregar
# ==========================
async def agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    carritos.setdefault(uid, [])
    if len(context.args) < 2:
        await update.effective_message.reply_text("Uso correcto: /agregar ID_PRODUCTO CANTIDAD")
        return

    try:
        pid = int(context.args[0])
        cant = int(context.args[1])
    except:
        await update.effective_message.reply_text("ID y cantidad deben ser números.")
        return

    try:
        r = requests.get(f"{API_URL}/productos/{pid}", timeout=10)
        if r.status_code != 200:
            await update.effective_message.reply_text("❌ Producto no encontrado.")
            return
        producto = r.json()
    except:
        await update.effective_message.reply_text("❌ Error conectando con la API.")
        return

    if producto.get("Stock", 0) < cant:
        await update.effective_message.reply_text(f"❌ Stock insuficiente. Disponible: {producto.get('Stock', 0)}")
        return

    carritos[uid].append({
        "producto_id": pid,
        "nombre": producto["Nombre"],
        "precio": producto["Precio"],
        "cantidad": cant
    })

    await update.effective_message.reply_text(
        f"✔ *{producto['Nombre']}* agregado x{cant}\n\n"
        "📌 Opciones:\n"
        "• /productos – Seguir comprando\n"
        "• /carrito – Ver tu carrito\n"
        "• /confirmar – Finalizar pedido\n"
        "• /cancelar – Vaciar carrito",
        parse_mode="Markdown"
    )

# ==========================
# /carrito
# ==========================
async def carrito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    items = carritos.get(uid, [])

    if not items:
        await update.effective_message.reply_text("🛒 Tu carrito está vacío.")
        return

    total = 0
    msg = "🛒 *Tu carrito:*\n\n"
    for i in items:
        subtotal = i["precio"] * i["cantidad"]
        total += subtotal
        msg += f"{i['nombre']} x{i['cantidad']} — ${subtotal}\n"

    msg += f"\n💰 *Total:* ${total}\n\n📌 Usa /confirmar para completar tu pedido."
    await update.effective_message.reply_text(msg, parse_mode="Markdown")

# ==========================
# /confirmar
# ==========================
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    items = carritos.get(uid, [])

    if not items:
        await update.effective_message.reply_text("Tu carrito está vacío.")
        return ConversationHandler.END

    registrar_pedido(uid)

    if necesita_captcha(uid):
        return await pedir_captcha(update, context)

    await update.effective_message.reply_text("📍 Envíame tu dirección completa:")
    return ESPERANDO_DIRECCION

async def recibir_direccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["direccion"] = update.effective_message.text
    await update.effective_message.reply_text("📞 Ahora envíame tu número de teléfono:")
    return ESPERANDO_TELEFONO

async def recibir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    items = carritos.get(uid, [])
    business_id = usuarios_negocio.get(uid)
    direccion = context.user_data.get("direccion")
    telefono = update.effective_message.text

    if not business_id:
        await update.effective_message.reply_text("❌ Primero elige un negocio usando /start.")
        return ConversationHandler.END

    payload = {
        "usuario_id": uid,
        "business_id": business_id,
        "direccion": direccion,
        "telefono": telefono,
        "productos": [{"producto_id": i["producto_id"], "cantidad": i["cantidad"]} for i in items]
    }

    try:
        r = requests.post(f"{API_URL}/pedidos", json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            carritos[uid] = []
            await update.effective_message.reply_text(
                f"✅ *Pedido confirmado*\n"
                f"🧾 ID: {data['pedido_id']}\n"
                f"💰 Total: ${data['total']}\n\n"
                "📌 Opciones:\n"
                "• /mispedidos – Ver estado de tus pedidos\n"
                "• /productos – Seguir comprando\n"
                "• /start – Cambiar de negocio",
                parse_mode="Markdown"
            )
        else:
            try:
                msg = r.json().get("detail")
            except:
                msg = r.text
            await update.effective_message.reply_text(f"❌ Error al crear el pedido: {msg}")
    except:
        await update.effective_message.reply_text("❌ Error conectando con la API.")
    return ConversationHandler.END

# ==========================
# /mispedidos
# ==========================
async def mispedidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    try:
        r = requests.get(f"{API_URL}/pedidos/usuario/{uid}", timeout=10)
        if r.status_code != 200:
            await update.effective_message.reply_text("❌ Error al obtener pedidos.")
            return
        pedidos = r.json()
    except:
        await update.effective_message.reply_text("❌ Error conectando con la API.")
        return

    if not pedidos:
        await update.effective_message.reply_text("No tienes pedidos aún.")
        return

    msg = "📄 *Tus pedidos:*\n\n"
    for p in pedidos:
        msg += f"🆔 {p['Id']} — Total: ${p['Total']} — Estado: {p['Estado']}\n"
    msg += "\n📌 También puedes:\n• /productos – Ver catálogo\n• /start – Cambiar de negocio\n"
    await update.effective_message.reply_text(msg, parse_mode="Markdown")

# ==========================
# /cancelar
# ==========================
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    carritos[uid] = []
    await update.effective_message.reply_text(
        "🗑️ Carrito vaciado.\n\n"
        "Puedes volver al catálogo con /productos\n"
        "o cambiar de negocio usando /start."
    )

# ==========================
# MAIN
# ==========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ConversationHandler para elegir negocio
    conv_negocio = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={ESPERANDO_NEGOCIO: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_negocio),
            CallbackQueryHandler(recibir_negocio)
        ]},
        fallbacks=[],
        per_user=True
    )

    # ConversationHandler para confirmar pedido
    conv_confirmar = ConversationHandler(
        entry_points=[CommandHandler("confirmar", confirmar)],
        states={
            ESPERANDO_CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, validar_captcha)],
            ESPERANDO_DIRECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_direccion)],
            ESPERANDO_TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_telefono)]
        },
        fallbacks=[],
        per_user=True
    )

    # Agregar handlers
    app.add_handler(conv_negocio)
    app.add_handler(conv_confirmar)
    app.add_handler(CommandHandler("productos", productos))
    app.add_handler(CommandHandler("agregar", agregar))
    app.add_handler(CommandHandler("carrito", carrito))
    app.add_handler(CommandHandler("mispedidos", mispedidos))
    app.add_handler(CommandHandler("cancelar", cancelar))

    print("Bot iniciado…")
    app.run_polling()

if __name__ == "__main__":
    main()
