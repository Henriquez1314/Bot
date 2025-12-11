# BotE-Commerce

BotE-Commerce es un sistema de comercio electrónico que integra un Bot de Telegram, una API REST desarrollada con FastAPI y una base de datos PostgreSQL.

# Estructura del Proyecto
BotE-Commerce/
│
├── api/
│   ├── main.py
│   ├── db.py
│   ├── models.py
│   └── config.py
│
├── bot/
│   ├── bot.py
│
├── requirements.txt
└── README.md

# Tecnologías Utilizadas

Python 3.10+

FastAPI

PostgreSQL

SQLAlchemy

python-telegram-bot v21

Uvicorn

python-dotenv

Requests

# Requisitos Previos

Python instalado

PostgreSQL instalado

Bot creado mediante BotFather

# Instalación
1. Clonar repositorio
git clone https://github.com/Henriquez1314/Bot.git
cd BotE-Commerce

2. Crear entorno virtual
python -m venv venv


Activar:
Windows: venv\Scripts\activate
Linux/macOS: source venv/bin/activate

3. Instalar dependencias
pip install -r requirements.txt

# Configuración de PostgreSQL

Crear base de datos:
CREATE DATABASE chatbotdb;

# Variables de Entorno
Crear archivo .env en la raíz del proyecto:

TELEGRAM_TOKEN=TU_TOKEN_DEL_BOT
API_URL=http://127.0.0.1:8000
DATABASE_URL=postgresql://usuario:password@localhost:5432/chatbotdb


⚠️ Nunca subas .env a GitHub, contiene información sensible.

# Ejecutar API
uvicorn api.main:app --reload

La API estará disponible en:

http://127.0.0.1:8000

# Ejecutar Bot
python bot/bot.py

El bot se conectará a Telegram usando el token definido en .env y consumirá la API local.

# Endpoints Disponibles

Productos

GET /productos → Listar todos los productos

GET /productos/{id} → Obtener producto por ID

POST /productos → Crear producto

PUT /productos/{id} → Actualizar producto

DELETE /productos/{id} → Eliminar producto

Pedidos

POST /pedidos → Crear un pedido

GET /pedidos/usuario/{id} → Obtener pedidos de un usuario

PUT /pedidos/{id}/cancelar → Cancelar un pedido
