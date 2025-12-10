import requests
import random
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

BOT_TOKEN = "8312937932:AAG2MfzeSVXOflTLxqRm-uvvpe0srovE-8c"
API_URL = "http://127.0.0.1:8000"

# ==========================
# Estados de conversación
# ==========================
ESPERANDO_NEGOCIO, ESPERANDO_DIRECCION, ESPERANDO_TELEFONO, ESPERANDO_CAPTCHA = range(4)

# Carritos, negocios y seguridad
carritos = {}
usuarios_negocio = {}

# Historial anti-spam
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

    # limpiar últimos 10 minutos
    historial_pedidos[uid] = [
        t for t in historial_pedidos[uid] if ahora - t < 600
    ]


def necesita_captcha(uid: int):
    return uid in historial_pedidos and len(historial_pedidos[uid]) >= 5


async def pedir_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id

    a = random.randint(1, 10)
    b = random.randint(1, 10)
    resultado = a + b

    captcha_pendiente[uid] = {"resultado": resultado}
    captcha_modo[uid] = True

    await update.message.reply_text(
        f"🔒 *Seguridad anti-spam*\n\n"
        f"Has hecho varios pedidos en poco tiempo.\n"
        f"Resuelve este captcha para continuar:\n\n"
        f"➡ ¿Cuánto es *{a} + {b}*?",
        parse_mode="Markdown"
    )
    return ESPERANDO_CAPTCHA


async def validar_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    texto = update.message.text

    if not texto.isdigit():
        await update.message.reply_text("❌ Debes responder con un número. Intenta de nuevo.")
        return ESPERANDO_CAPTCHA

    if int(texto) != captcha_pendiente[uid]["resultado"]:
        await update.message.reply_text("❌ Captcha incorrecto. Intenta otra vez.")
        return ESPERANDO_CAPTCHA

    captcha_modo[uid] = False
    await update.message.reply_text("🔓 Captcha correcto. Continuemos.")

    await update.message.reply_text("📍 Envíame tu dirección completa:")
    return ESPERANDO_DIRECCION


# ==========================
# /start — inicio
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bienvenido al Bot E-Commerce*\n\n"
        "Para comenzar, envía el *ID del negocio* con el que deseas comprar.\n\n",
        parse_mode="Markdown"
    )
    return ESPERANDO_NEGOCIO


async def recibir_negocio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    try:
        business_id = int(update.message.text)

        r = requests.get(f"{API_URL}/negocio/{business_id}")
        if r.status_code != 200:
            await update.message.reply_text("❌ Ese negocio no existe. Intenta nuevamente.")
            return ESPERANDO_NEGOCIO

        data = r.json()
        nombre_negocio = data["Nombre"]

        usuarios_negocio[uid] = business_id

        await update.message.reply_text(
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

    except ValueError:
        await update.message.reply_text("Por favor, ingresa un número válido.")
        return ESPERANDO_NEGOCIO

    return ConversationHandler.END


# ==========================
# /productos
# ==========================
async def productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    business_id = usuarios_negocio.get(uid)

    if not business_id:
        await update.message.reply_text("❌ Primero selecciona un negocio usando /start.")
        return

    try:
        res = requests.get(f"{API_URL}/productos?business_id={business_id}")
        prods = res.json()
    except:
        await update.message.reply_text("❌ Error conectando con la API.")
        return

    if not prods:
        await update.message.reply_text("No hay productos disponibles.")
        return

    await update.message.reply_text(
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
            await update.message.reply_photo(photo=p["ImagenUrl"], caption=texto, parse_mode="Markdown")
        else:
            await update.message.reply_text(texto, parse_mode="Markdown")


# ==========================
# /agregar
# ==========================
async def agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    carritos.setdefault(uid, [])

    if len(context.args) < 2:
        await update.message.reply_text("Uso correcto: /agregar ID_PRODUCTO CANTIDAD")
        return

    try:
        pid = int(context.args[0])
        cant = int(context.args[1])
    except:
        await update.message.reply_text("ID y cantidad deben ser números.")
        return

    r = requests.get(f"{API_URL}/productos/{pid}")
    if r.status_code != 200:
        await update.message.reply_text("❌ Producto no encontrado.")
        return

    producto = r.json()

    if producto.get("Stock", 0) < cant:
        await update.message.reply_text(f"❌ Stock insuficiente. Disponible: {producto.get('Stock', 0)}")
        return

    carritos[uid].append({
        "producto_id": pid,
        "nombre": producto["Nombre"],
        "precio": producto["Precio"],
        "cantidad": cant
    })

    await update.message.reply_text(
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
    uid = update.message.from_user.id
    items = carritos.get(uid, [])

    if not items:
        await update.message.reply_text("🛒 Tu carrito está vacío.")
        return

    msg = "🛒 *Tu carrito:*\n\n"
    total = 0
    for i in items:
        subtotal = i["precio"] * i["cantidad"]
        total += subtotal
        msg += f"{i['nombre']} x{i['cantidad']} — ${subtotal}\n"

    msg += f"\n💰 *Total:* ${total}\n\n📌 Usa /confirmar para completar tu pedido."

    await update.message.reply_text(msg, parse_mode="Markdown")


# ==========================
# /confirmar
# ==========================
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    items = carritos.get(uid, [])

    if not items:
        await update.message.reply_text("Tu carrito está vacío.")
        return ConversationHandler.END

    registrar_pedido(uid)

    if necesita_captcha(uid):
        return await pedir_captcha(update, context)

    await update.message.reply_text("📍 Envíame tu dirección completa:")
    return ESPERANDO_DIRECCION


# ==========================
# recibir dirección
# ==========================
async def recibir_direccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["direccion"] = update.message.text
    await update.message.reply_text("📞 Ahora envíame tu número de teléfono:")
    return ESPERANDO_TELEFONO


# ==========================
# recibir teléfono y crear pedido
# ==========================
async def recibir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telefono = update.message.text
    direccion = context.user_data["direccion"]
    uid = update.message.from_user.id
    items = carritos.get(uid, [])

    business_id = usuarios_negocio.get(uid)
    if not business_id:
        await update.message.reply_text("❌ Primero elige un negocio usando /start.")
        return ConversationHandler.END

    payload = {
        "usuario_id": uid,
        "business_id": business_id,
        "direccion": direccion,
        "telefono": telefono,
        "productos": [{"producto_id": i["producto_id"], "cantidad": i["cantidad"]} for i in items]
    }

    r = requests.post(f"{API_URL}/pedidos", json=payload)

    if r.status_code == 200:
        data = r.json()
        carritos[uid] = []

        await update.message.reply_text(
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
        await update.message.reply_text(f"❌ Error al crear el pedido: {msg}")

    return ConversationHandler.END


# ==========================
# /mispedidos
# ==========================
async def mispedidos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    r = requests.get(f"{API_URL}/pedidos/usuario/{uid}")

    if r.status_code != 200:
        await update.message.reply_text("❌ Error al obtener pedidos.")
        return

    pedidos = r.json()

    if not pedidos:
        await update.message.reply_text("No tienes pedidos aún.")
        return

    msg = "📄 *Tus pedidos:*\n\n"
    for p in pedidos:
        msg += f"🆔 {p['Id']} — Total: ${p['Total']} — Estado: {p['Estado']}\n"

    msg += (
        "\n📌 También puedes:\n"
        "• /productos – Ver catálogo\n"
        "• /start – Cambiar de negocio\n"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")


# ==========================
# /cancelar
# ==========================
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    carritos[uid] = []

    await update.message.reply_text(
        "🗑️ Carrito vaciado.\n\n"
        "Puedes volver al catálogo con /productos\n"
        "o cambiar de negocio usando /start."
    )


# ==========================
# MAIN
# ==========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_inicio = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ESPERANDO_NEGOCIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_negocio)]
        },
        fallbacks=[]
    )

    conv_confirmar = ConversationHandler(
        entry_points=[CommandHandler("confirmar", confirmar)],
        states={
            ESPERANDO_CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, validar_captcha)],
            ESPERANDO_DIRECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_direccion)],
            ESPERANDO_TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_telefono)]
        },
        fallbacks=[]
    )

    app.add_handler(conv_inicio)
    app.add_handler(CommandHandler("productos", productos))
    app.add_handler(CommandHandler("agregar", agregar))
    app.add_handler(CommandHandler("carrito", carrito))
    app.add_handler(conv_confirmar)
    app.add_handler(CommandHandler("mispedidos", mispedidos))
    app.add_handler(CommandHandler("cancelar", cancelar))

    print("Bot iniciado…")
    app.run_polling()


if __name__ == "__main__":
    main()
