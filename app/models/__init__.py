"""
Modelos de base de datos para la plataforma de transporte a Paraguay.
Todas las tablas usan UUID como clave primaria para evitar colisiones
y facilitar la sincronización entre sistemas.
"""

import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    UUID, Boolean, Date, DateTime, Enum, Float,
    ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enumerados — se usan tanto en la BD como en la API
# ---------------------------------------------------------------------------

import enum


class EstadoEnvio(str, enum.Enum):
    pendiente_recogida = "pendiente_recogida"
    recogido = "recogido"
    en_almacen = "en_almacen"
    asignado_contenedor = "asignado_contenedor"
    en_transito = "en_transito"
    llego_paraguay = "llego_paraguay"
    en_distribucion = "en_distribucion"
    entregado = "entregado"


class EstadoContenedor(str, enum.Enum):
    llenando = "llenando"
    cerrado = "cerrado"
    en_transito = "en_transito"
    llego = "llego"
    distribuyendo = "distribuyendo"
    completado = "completado"


class TipoPago(str, enum.Enum):
    inicial = "inicial"
    parcial = "parcial"
    saldo = "saldo"
    total = "total"


class MetodoPago(str, enum.Enum):
    efectivo = "efectivo"
    transferencia = "transferencia"
    bizum = "bizum"


class EstadoPago(str, enum.Enum):
    pendiente = "pendiente"
    declarado_cliente = "declarado_cliente"
    verificado = "verificado"
    rechazado = "rechazado"


# ---------------------------------------------------------------------------
# Tabla: CLIENTES
# ---------------------------------------------------------------------------

class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Nombre completo en campos separados para evitar ambigüedades
    primer_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    segundo_nombre: Mapped[Optional[str]] = mapped_column(String(100))
    primer_apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    segundo_apellido: Mapped[Optional[str]] = mapped_column(String(100))

    # Identificación — se alerta al gestor si cambia el DNI
    dni_actual: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Contacto en España
    telefono_principal: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    telefono_alternativo: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    telegram_user: Mapped[Optional[str]] = mapped_column(String(100))
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(50))

    # Dirección de recogida en España
    direccion_recogida: Mapped[str] = mapped_column(Text, nullable=False)

    # Datos del destinatario en Paraguay
    nombre_destinatario_py: Mapped[str] = mapped_column(String(200), nullable=False)
    telefono_destinatario_py: Mapped[str] = mapped_column(String(20), nullable=False)
    direccion_destino_py: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadatos
    fecha_alta: Mapped[date] = mapped_column(Date, nullable=True, default=date.today)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    notas: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
    historial_cambios: Mapped[List["HistorialCambioCliente"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan"
    )
    envios: Mapped[List["Envio"]] = relationship(
        back_populates="cliente"
    )

    @property
    def nombre_completo(self) -> str:
        partes = [self.primer_nombre, self.segundo_nombre,
                  self.primer_apellido, self.segundo_apellido]
        return " ".join(p for p in partes if p)

    def __repr__(self) -> str:
        return f"<Cliente {self.nombre_completo} DNI={self.dni_actual}>"


# ---------------------------------------------------------------------------
# Tabla: HISTORIAL_CAMBIOS_CLIENTE
# Nunca se sobreescriben datos — todo cambio queda registrado aquí
# ---------------------------------------------------------------------------

class HistorialCambioCliente(Base):
    __tablename__ = "historial_cambios_cliente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False
    )
    campo_modificado: Mapped[str] = mapped_column(String(100), nullable=False)
    valor_anterior: Mapped[Optional[str]] = mapped_column(Text)
    valor_nuevo: Mapped[Optional[str]] = mapped_column(Text)
    fecha_cambio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    usuario_cambio: Mapped[str] = mapped_column(String(100), nullable=False, default="sistema")

    # Relaciones
    cliente: Mapped["Cliente"] = relationship(back_populates="historial_cambios")

    def __repr__(self) -> str:
        return f"<Cambio {self.campo_modificado} cliente={self.cliente_id}>"


# ---------------------------------------------------------------------------
# Tabla: CONTENEDORES
# ---------------------------------------------------------------------------

class Contenedor(Base):
    __tablename__ = "contenedores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    numero_contenedor: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    estado: Mapped[EstadoContenedor] = mapped_column(
        Enum(EstadoContenedor), nullable=False, default=EstadoContenedor.llenando
    )

    # Capacidad — para calcular % de llenado y lanzar alerta al 90%
    capacidad_m3: Mapped[Optional[float]] = mapped_column(Float)
    volumen_ocupado_m3: Mapped[float] = mapped_column(Float, default=0.0)

    # Fechas clave del ciclo de vida
    fecha_apertura: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    fecha_cierre: Mapped[Optional[date]] = mapped_column(Date)
    fecha_envio: Mapped[Optional[date]] = mapped_column(Date)
    fecha_llegada_paraguay: Mapped[Optional[date]] = mapped_column(Date)

    notas: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
    envios: Mapped[List["Envio"]] = relationship(back_populates="contenedor")

    @property
    def porcentaje_llenado(self) -> Optional[float]:
        if self.capacidad_m3 and self.capacidad_m3 > 0:
            return round((self.volumen_ocupado_m3 / self.capacidad_m3) * 100, 1)
        return None

    def __repr__(self) -> str:
        return f"<Contenedor {self.numero_contenedor} estado={self.estado}>"


# ---------------------------------------------------------------------------
# Tabla: ENVIOS
# ---------------------------------------------------------------------------

class Envio(Base):
    __tablename__ = "envios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Código visible y legible: ENV-2024-0001
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    # Relaciones clave
    cliente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False
    )
    contenedor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contenedores.id")
    )

    # Descripción del producto
    descripcion_producto: Mapped[str] = mapped_column(Text, nullable=False)
    peso_kg: Mapped[Optional[float]] = mapped_column(Float)
    volumen_m3: Mapped[Optional[float]] = mapped_column(Float)

    # Precio y estado de pago
    precio_total: Mapped[float] = mapped_column(Float, nullable=False)

    # Estado del envío
    estado: Mapped[EstadoEnvio] = mapped_column(
        Enum(EstadoEnvio), nullable=False, default=EstadoEnvio.pendiente_recogida
    )

    # Fechas
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_recogida_pactada: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fecha_recogida_real: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    fecha_entrega: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Archivos (URLs a Cloudflare R2 — nunca blobs en la BD)
    qr_code_url: Mapped[Optional[str]] = mapped_column(Text)
    firma_url: Mapped[Optional[str]] = mapped_column(Text)
    # Lista de URLs de fotos — se almacena como texto separado por comas
    # En PostgreSQL podría usarse ARRAY, pero Text es más portable
    fotos_urls: Mapped[Optional[str]] = mapped_column(Text)  # JSON string de lista

    notas: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
    cliente: Mapped["Cliente"] = relationship(back_populates="envios")
    contenedor: Mapped[Optional["Contenedor"]] = relationship(back_populates="envios")
    pagos: Mapped[List["Pago"]] = relationship(
        back_populates="envio", cascade="all, delete-orphan"
    )

    @property
    def total_pagado(self) -> float:
        return sum(
            p.monto for p in self.pagos
            if p.estado == EstadoPago.verificado
        )

    @property
    def saldo_pendiente(self) -> float:
        return round(self.precio_total - self.total_pagado, 2)

    @property
    def tiene_deuda(self) -> bool:
        return self.saldo_pendiente > 0

    def __repr__(self) -> str:
        return f"<Envio {self.codigo} estado={self.estado}>"


# ---------------------------------------------------------------------------
# Tabla: PAGOS
# ---------------------------------------------------------------------------

class Pago(Base):
    __tablename__ = "pagos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    envio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("envios.id", ondelete="CASCADE"), nullable=False
    )

    monto: Mapped[float] = mapped_column(Float, nullable=False)
    tipo: Mapped[TipoPago] = mapped_column(Enum(TipoPago), nullable=False)
    metodo: Mapped[MetodoPago] = mapped_column(Enum(MetodoPago), nullable=False)
    estado: Mapped[EstadoPago] = mapped_column(
        Enum(EstadoPago), nullable=False, default=EstadoPago.pendiente
    )

    # El cliente puede declarar el pago desde el portal o Telegram
    declarado_por_cliente: Mapped[bool] = mapped_column(Boolean, default=False)

    # URL del comprobante subido a R2
    comprobante_url: Mapped[Optional[str]] = mapped_column(Text)

    fecha_pago: Mapped[Optional[date]] = mapped_column(Date)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_verificacion: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    verificado_por: Mapped[Optional[str]] = mapped_column(String(100))

    notas: Mapped[Optional[str]] = mapped_column(Text)

    # Relaciones
    envio: Mapped["Envio"] = relationship(back_populates="pagos")

    def __repr__(self) -> str:
        return f"<Pago {self.monto}€ {self.estado} envio={self.envio_id}>"
