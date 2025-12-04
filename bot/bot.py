import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

BOT_TOKEN = "8312937932:AAG2MfzeSVXOflTLxqRm-uvvpe0srovE-8c"
API_URL = "http://127.0.0.1:8000"  

# Estados de conversación para confirmar pedido
ESPERANDO_DIRECCION, ESPERANDO_TELEFONO = range(2)

# Carritos por usuario
carritos = {}


# ==========================
# /start — menú principal
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 *Bienvenido al Bot E-Commerce*\n\n"
        "Aquí tienes los comandos disponibles:\n\n"
        "📦 /productos — Ver catálogo y agregar productos\n"
        "🛒 /carrito — Ver tu carrito actual\n"
        "✅ /confirmar — Confirmar pedido\n"
        "📄 /mispedidos — Ver tus pedidos\n"
        "❌ /cancelar — Cancelar pedido\n\n"
        "Para agregar un producto al carrito, usa:\n"
        "`/agregar ID_PRODUCTO CANTIDAD`\n"
        "Ejemplo: `/agregar 3 2`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ==========================
# /productos — muestra catálogo
# ==========================
async def productos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        res = requests.get(f"{API_URL}/productos")
        prods = res.json()
    except:
        await update.message.reply_text("❌ Error conectando con la API.")
        return

    if not prods:
        await update.message.reply_text("No hay productos disponibles.")
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
            await update.message.reply_photo(
                photo=p["ImagenUrl"],
                caption=texto,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(texto, parse_mode="Markdown")


# bot/bot.py (fragmentos)
import requests
from config import BOT_TOKEN, API_URL

# ... resto igual ...

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

    # Verificar producto en API
    r = requests.get(f"{API_URL}/productos/{pid}")
    if r.status_code != 200:
        await update.message.reply_text("❌ Producto no encontrado.")
        return

    producto = r.json()
    if producto.get("Stock", 0) < cant:
        await update.message.reply_text(f"❌ Stock insuficiente. Disponible: {producto.get('Stock',0)}")
        return

    carritos[uid].append({"producto_id": pid, "nombre": producto["Nombre"],
                          "precio": producto["Precio"], "cantidad": cant})

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
# /confirmar — inicia conversación para datos
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

    payload = {
        "usuario_id": uid,
        "direccion": direccion,
        "telefono": telefono,
        "productos": [{"producto_id": i["producto_id"], "cantidad": i["cantidad"]} for i in items]
    }

    r = requests.post(f"{API_URL}/pedidos", json=payload)
    if r.status_code == 200:
        data = r.json()
        carritos[uid] = []  # vaciar carrito
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

    # Comandos normales
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("productos", productos))
    app.add_handler(CommandHandler("agregar", agregar))
    app.add_handler(CommandHandler("carrito", carrito))
    app.add_handler(CommandHandler("mispedidos", mispedidos))
    app.add_handler(CommandHandler("cancelar", cancelar))

    # Conversación para confirmar pedido
    conv = ConversationHandler(
        entry_points=[CommandHandler("confirmar", confirmar)],
        states={
            ESPERANDO_DIRECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_direccion)],
            ESPERANDO_TELEFONO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_telefono)]
        },
        fallbacks=[]
    )
    app.add_handler(conv)

    print("Bot iniciado…")
    app.run_polling()


if __name__ == "__main__":
    main()
