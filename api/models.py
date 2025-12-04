# api/models.py (solo mostrar modificaciones relevantes)
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Producto(Base):
    __tablename__ = "Productos"

    Id = Column(Integer, primary_key=True, index=True)
    Nombre = Column(String(255), nullable=False)
    Descripcion = Column(String(500), nullable=True)
    DescripcionCorta = Column(String(255), nullable=True)
    Precio = Column(Float, nullable=False)
    ImagenUrl = Column(String(500), nullable=True)
    Stock = Column(Integer, default=0)   # <- nueva columna

    detalles = relationship("PedidoDetalle", back_populates="producto")


class Pedido(Base):
    __tablename__ = "Pedidos"

    Id = Column(Integer, primary_key=True, index=True)
    UsuarioId = Column(BigInteger, nullable=False)   # ← CORREGIDO (antes Integer)
    Direccion = Column(String(300))
    Telefono = Column(String(50))
    FechaPedido = Column(DateTime)
    FechaCreacion = Column(DateTime)
    FechaActualizacion = Column(DateTime)
    Total = Column(Float, default=0)
    Estado = Column(String(20), default="pendiente")

    detalles = relationship("PedidoDetalle", back_populates="pedido", cascade="all, delete")


class PedidoDetalle(Base):
    __tablename__ = "PedidoDetalles"

    Id = Column(Integer, primary_key=True, index=True)
    PedidoId = Column(Integer, ForeignKey("Pedidos.Id"))
    ProductoId = Column(Integer, ForeignKey("Productos.Id"))
    Cantidad = Column(Integer, nullable=False)
    PrecioUnitario = Column(Float, nullable=False)
    TotalLinea = Column(Float, nullable=False)

    pedido = relationship("Pedido", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles")
