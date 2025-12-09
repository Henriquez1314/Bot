import requests
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
ESPERANDO_NEGOCIO, ESPERANDO_DIRECCION, ESPERANDO_TELEFONO = range(3)

# Carritos y negocio por usuario
carritos = {}
usuarios_negocio = {}

# ==========================
# /start — inicio y seleccionar empresa
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 *Bienvenido al Bot E-Commerce*\n\n"
        "Primero, seleccionemos la empresa/negocio para ver su catálogo.\n\n"
        "Por favor, ingresa el ID de la empresa/negocio:"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return ESPERANDO_NEGOCIO

async def recibir_negocio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    try:
        business_id = int(update.message.text)
        usuarios_negocio[uid] = business_id
        await update.message.reply_text(f"✅ Negocio {business_id} seleccionado. Ahora puedes ver los productos con /productos.")
    except ValueError:
        await update.message.reply_text("Por favor, ingresa un número válido.")
        return ESPERANDO_NEGOCIO
    return ConversationHandler.END

# ==========================
# /productos — mostrar catálogo usando business_id guardado
# ==========================
async def productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    business_id = usuarios_negocio.get(uid)

    if not business_id:
        await update.message.reply_text(
            "❌ Primero debes seleccionar una empresa/negocio usando /start."
        )
        return

    try:
        res = requests.get(f"{API_URL}/productos?business_id={business_id}")
        prods = res.json()
    except:
        await update.message.reply_text("❌ Error conectando con la API.")
        return

    if not prods:
        await update.message.reply_text("No hay productos disponibles para este negocio.")
        return

    for p in prods:
        texto = (
            f"🆔 *ID:* {p['Id']}\n"
            f"📦 *{p['Nombre']}*\n"
            f"💲 Precio: ${p['Precio']}\n"
            f"📃 {p.get('DescripcionCorta','')}\n"
            f"Para agregar: `/agregar {p['Id']} 1`"
        )
        if p.get("ImagenUrl"):
            await update.message.reply_photo(photo=p["ImagenUrl"], caption=texto, parse_mode="Markdown")
        else:
            await update.message.reply_text(texto, parse_mode="Markdown")

# ==========================
# /agregar — agregar producto al carrito
# ==========================
async def agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    carritos.setdefault(uid, [])

    if len(context.args) < 2:
        await update.message.reply_text("Uso: /agregar ID_PRODUCTO CANTIDAD")
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
        await update.message.reply_text(f"❌ Stock insuficiente. Disponible: {producto.get('Stock',0)}")
        return

    carritos[uid].append({
        "producto_id": pid,
        "nombre": producto["Nombre"],
        "precio": producto["Precio"],
        "cantidad": cant
    })

    await update.message.reply_text(f"✔ *{producto['Nombre']}* agregado x{cant}", parse_mode="Markdown")

# ==========================
# /carrito — muestra carrito
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

    msg += f"\n💰 *Total:* ${total}"
    await update.message.reply_text(msg, parse_mode="Markdown")

# ==========================
# /confirmar — iniciar datos para pedido
# ==========================
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    items = carritos.get(uid, [])
    if not items:
        await update.message.reply_text("Tu carrito está vacío.")
        return ConversationHandler.END

    await update.message.reply_text("📍 Por favor, envíame tu dirección completa:")
    return ESPERANDO_DIRECCION

async def recibir_direccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["direccion"] = update.message.text
    await update.message.reply_text("📞 Ahora envíame tu número de teléfono:")
    return ESPERANDO_TELEFONO

async def recibir_telefono(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telefono = update.message.text
    direccion = context.user_data["direccion"]
    uid = update.message.from_user.id
    items = carritos.get(uid, [])

    business_id = usuarios_negocio.get(uid)
    if not business_id:
        await update.message.reply_text("❌ Primero debes seleccionar un negocio con /start o /productos.")
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
            f"✅ Pedido confirmado\n🧾 ID: {data['pedido_id']}\n💰 Total: ${data['total']}"
        )
    else:
        try:
            err = r.json()
            msg = err.get('detail') or err
        except:
            msg = r.text
        await update.message.reply_text(f"❌ Error al crear el pedido: {msg}")
    return ConversationHandler.END

# ==========================
# /mispedidos — ver pedidos
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
    await update.message.reply_text(msg, parse_mode="Markdown")

# ==========================
# /cancelar — cancelar pedido actual
# ==========================
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    carritos[uid] = []
    await update.message.reply_text("❌ Pedido cancelado.")

# ==========================
# MAIN
# ==========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Conversación inicio -> seleccionar negocio
    conv_inicio = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ESPERANDO_NEGOCIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_negocio)]
        },
        fallbacks=[]
    )

    # Conversación confirmación de pedido
    conv_confirmar = ConversationHandler(
    entry_points=[CommandHandler("confirmar", confirmar)],
    states={
        ESPERANDO_DIRECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_direccion)],
        ESPERANDO_TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_telefono)]
    },
    fallbacks=[]
)


    # Agregar handlers
    app.add_handler(conv_inicio)
    app.add_handler(CommandHandler("productos", productos))  # Mostrar catálogo usando business_id guardado
    app.add_handler(CommandHandler("agregar", agregar))
    app.add_handler(CommandHandler("carrito", carrito))
    app.add_handler(conv_confirmar)
    app.add_handler(CommandHandler("mispedidos", mispedidos))
    app.add_handler(CommandHandler("cancelar", cancelar))

    print("Bot iniciado…")
    app.run_polling()

if __name__ == "__main__":
    main()
