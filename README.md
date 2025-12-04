# BotE-Commerce

BotE-Commerce es un sistema de comercio electrónico que integra un Bot
de Telegram, una API REST desarrollada con FastAPI, una base de datos
PostgreSQL y un Panel de Administración Web.

## Estructura del Proyecto

    BotE-Commerce/
    │
    ├── api/
    │   ├── main.py
    │   ├── db.py
    │   ├── models.py
    │
    ├── bot/
    │   ├── bot.py
    │   ├── config.py
    │
    └── README.md

## Tecnologías Utilizadas

-   Python 3.10+
-   FastAPI
-   PostgreSQL
-   SQLAlchemy
-   python-telegram-bot v21
-   Uvicorn
-   HTML, JavaScript (panel administrativo)

## Requisitos Previos

-   Python instalado
-   PostgreSQL instalado
-   Bot creado mediante BotFather

## Instalación

### 1. Clonar repositorio

    git clone https://github.com/Henriquez1314/Bot.git
    cd BotE-Commerce

### 2. Crear entorno virtual

    python -m venv venv

Activar: - Windows: `venv\Scripts\activate` - Linux/macOS:
`source venv/bin/activate`

### 3. Instalar dependencias

    pip install -r requirements.txt

## Configuración de PostgreSQL

Crear base:

    CREATE DATABASE chatbotdb;

## Variables de Entorno

Crear archivo `.env`:

    TELEGRAM_TOKEN=TU_TOKEN
    API_URL=http://localhost:8000
    DATABASE_URL=postgresql://usuario:password@localhost:5432/chatbotdb
    ADMIN_KEY=mi_admin_key_secreto

## Ejecutar API

    uvicorn main:app --reload

Panel admin:

    http://localhost:8000/panel

## Ejecutar Bot

    python bot.py

## Seguridad

El header requerido para admin:

    x-admin-key: tu_clave_admin

## Endpoints

### Productos

-   GET /productos
-   GET /productos/{id}
-   POST /admin/productos
-   PUT /admin/productos/{id}
-   DELETE /admin/productos/{id}

### Pedidos

-   POST /pedidos
-   GET /pedidos/usuario/{id}
-   PUT /pedidos/{id}/cancelar
-   GET /admin/pedidos
-   PUT /admin/pedidos/{id}/estado

## Licencia

MIT
