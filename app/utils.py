"""
Utilidades compartidas:
- Generador de códigos de envío legibles (ENV-YYYY-XXXX)
- Detector de duplicados de clientes
- Búsqueda fonética aproximada
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Envio, Cliente


def generar_codigo_envio(db: Session) -> str:
    """
    Genera el siguiente código de envío correlativo para el año actual.
    Formato: ENV-2024-0001, ENV-2024-0002, ...
    """
    year = datetime.now().year
    prefijo = f"ENV-{year}-"

    ultimo = (
        db.query(Envio)
        .filter(Envio.codigo.like(f"{prefijo}%"))
        .order_by(Envio.codigo.desc())
        .first()
    )

    if ultimo is None:
        siguiente = 1
    else:
        try:
            siguiente = int(ultimo.codigo.split("-")[-1]) + 1
        except (ValueError, IndexError):
            siguiente = 1

    return f"{prefijo}{siguiente:04d}"


def buscar_duplicados_cliente(
    db: Session,
    dni: str,
    telefono: str,
    excluir_id=None,
) -> list[Cliente]:
    """
    Devuelve clientes con el mismo DNI o teléfono principal.
    Se usa al crear o editar un cliente para alertar de posibles duplicados.
    """
    query = db.query(Cliente).filter(
        (Cliente.dni_actual == dni) | (Cliente.telefono_principal == telefono)
    )
    if excluir_id:
        query = query.filter(Cliente.id != excluir_id)
    return query.all()


def normalizar_telefono(telefono: str) -> str:
    """
    Normaliza un teléfono eliminando espacios, guiones y el prefijo +34.
    Facilita la comparación entre registros.
    """
    tel = telefono.strip().replace(" ", "").replace("-", "")
    if tel.startswith("+34"):
        tel = tel[3:]
    return tel


def registrar_cambio_cliente(
    db: Session,
    cliente_id,
    campo: str,
    valor_anterior: str,
    valor_nuevo: str,
    usuario: str = "sistema",
) -> None:
    """
    Registra un cambio en el historial del cliente.
    Llamar antes de aplicar el cambio en el objeto Cliente.
    """
    from app.models import HistorialCambioCliente

    cambio = HistorialCambioCliente(
        cliente_id=cliente_id,
        campo_modificado=campo,
        valor_anterior=str(valor_anterior) if valor_anterior is not None else None,
        valor_nuevo=str(valor_nuevo) if valor_nuevo is not None else None,
        usuario_cambio=usuario,
    )
    db.add(cambio)
