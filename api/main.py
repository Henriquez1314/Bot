# api/main.py
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone
from .db import SessionLocal, engine
from . import models
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Bot E-Commerce")

# admin key (simple)
ADMIN_KEY = os.getenv("ADMIN_KEY", "mi_admin_key_secreto")

# ----- DB -----
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----- Schemas (extender si quieres) -----
class ProductoOut(BaseModel):
    Id: int
    Nombre: str
    Descripcion: str | None
    DescripcionCorta: str | None
    Precio: float
    ImagenUrl: str | None
    Stock: int

    class Config:
        orm_mode = True

class ProductoIn(BaseModel):
    Nombre: str
    Descripcion: str | None = None
    DescripcionCorta: str | None = None
    Precio: float
    ImagenUrl: str | None = None
    Stock: int = 0

# Pedido schemas (reusar)
class PedidoItem(BaseModel):
    producto_id: int
    cantidad: int

class PedidoCreate(BaseModel):
    usuario_id: int
    direccion: str
    telefono: str
    productos: list[PedidoItem]

# ---------------- PUBLIC ENDPOINTS (existentes) ----------------
@app.get("/productos", response_model=list[ProductoOut])
def listar_productos(db: Session = Depends(get_db)):
    return db.query(models.Producto).all()

@app.get("/productos/{pid}", response_model=ProductoOut)
def obtener_producto(pid: int, db: Session = Depends(get_db)):
    prod = db.query(models.Producto).filter(models.Producto.Id == pid).first()
    if not prod:
        raise HTTPException(404, "Producto no encontrado")
    return prod

# POST /pedidos: ahora validamos stock y creamos pedido (igual lógica, pero descontar stock)
@app.post("/pedidos")
def crear_pedido(data: PedidoCreate, db: Session = Depends(get_db)):
    nuevo = models.Pedido(
        UsuarioId=data.usuario_id,
        Direccion=data.direccion,
        Telefono=data.telefono,
        FechaPedido=datetime.now(timezone.utc),
        FechaCreacion=datetime.now(timezone.utc),
        FechaActualizacion=datetime.now(timezone.utc)
    )

    total = 0
    for item in data.productos:
        prod = db.query(models.Producto).filter(models.Producto.Id == item.producto_id).with_for_update().first()
        if not prod:
            raise HTTPException(404, f"Producto {item.producto_id} no existe")
        if prod.Stock < item.cantidad:
            raise HTTPException(400, f"Stock insuficiente para {prod.Nombre} (disponible: {prod.Stock})")

        subtotal = float(prod.Precio) * item.cantidad
        total += subtotal

        detalle = models.PedidoDetalle(
            ProductoId=item.producto_id,
            Cantidad=item.cantidad,
            PrecioUnitario=prod.Precio,
            TotalLinea=subtotal
        )

        nuevo.detalles.append(detalle)

        # descontar stock
        prod.Stock -= item.cantidad

    nuevo.Total = total

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    return {"pedido_id": nuevo.Id, "total": total}

@app.get("/pedidos/usuario/{uid}")
def pedidos_usuario(uid: int, db: Session = Depends(get_db)):
    return db.query(models.Pedido).filter(models.Pedido.UsuarioId == uid).all()

@app.put("/pedidos/{pid}/cancelar")
def cancelar_pedido(pid: int, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.Id == pid).first()
    if not pedido:
        raise HTTPException(404, "Pedido no existe")

    pedido.Estado = "cancelado"
    pedido.FechaActualizacion = datetime.now(timezone.utc)

    # devolver stock
    for d in pedido.detalles:
        prod = db.query(models.Producto).filter(models.Producto.Id == d.ProductoId).first()
        if prod:
            prod.Stock += d.Cantidad

    db.commit()
    return {"status": "cancelado"}

# ---------------- ADMIN ENDPOINTS (requieren x-admin-key header) ----------------
def require_admin(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

# Create product
@app.post("/admin/productos", dependencies=[Depends(require_admin)])
def admin_create_producto(p: ProductoIn, db: Session = Depends(get_db)):
    nuevo = models.Producto(
        Nombre=p.Nombre,
        Descripcion=p.Descripcion,
        DescripcionCorta=p.DescripcionCorta,
        Precio=p.Precio,
        ImagenUrl=p.ImagenUrl,
        Stock=p.Stock
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

# Update product
@app.put("/admin/productos/{pid}", dependencies=[Depends(require_admin)])
def admin_update_producto(pid: int, p: ProductoIn, db: Session = Depends(get_db)):
    prod = db.query(models.Producto).filter(models.Producto.Id == pid).first()
    if not prod:
        raise HTTPException(404, "Producto no encontrado")
    prod.Nombre = p.Nombre
    prod.Descripcion = p.Descripcion
    prod.DescripcionCorta = p.DescripcionCorta
    prod.Precio = p.Precio
    prod.ImagenUrl = p.ImagenUrl
    prod.Stock = p.Stock
    db.commit()
    return prod

# Delete product
@app.delete("/admin/productos/{pid}", dependencies=[Depends(require_admin)])
def admin_delete_producto(pid: int, db: Session = Depends(get_db)):
    prod = db.query(models.Producto).filter(models.Producto.Id == pid).first()
    if not prod:
        raise HTTPException(404, "Producto no encontrado")
    db.delete(prod)
    db.commit()
    return {"status": "deleted"}

# List all orders (admin)
@app.get("/admin/pedidos", dependencies=[Depends(require_admin)])
def admin_list_pedidos(db: Session = Depends(get_db)):
    return db.query(models.Pedido).order_by(models.Pedido.FechaCreacion.desc()).all()

# Update estado de pedido
@app.put("/admin/pedidos/{pid}/estado", dependencies=[Depends(require_admin)])
def admin_update_estado(pid: int, estado: str, db: Session = Depends(get_db)):
    pedido = db.query(models.Pedido).filter(models.Pedido.Id == pid).first()
    if not pedido:
        raise HTTPException(404, "Pedido no existe")
    pedido.Estado = estado
    pedido.FechaActualizacion = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok", "nuevo_estado": estado}

# ---------------- SERVIR PANEL ESTÁTICO ----------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent  # asume api/ dentro de BotE-Commerce
STATIC_DIR = BASE_DIR / "admin_panel" / "static"
HTML_DIR = BASE_DIR / "admin_panel"

app.mount("/panel/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/panel")
def panel_index():
    return FileResponse(str(HTML_DIR / "index.html"))
