import json
import os
import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

# Importamos las herramientas de tu paquete 'app'
from app.database import get_db
from app.models import Cliente

app = FastAPI()
templates = Jinja2Templates(directory="templates")
templates.env.cache = None


# ---------------------------------------------------------------------------
# Almacenamiento de fotos
# ---------------------------------------------------------------------------
# Por ahora guardamos las fotos en una carpeta local en el disco del
# servidor, para poder probar el formulario completo sin depender todavía
# de una cuenta de Cloudflare R2.
#
# IMPORTANTE: en Render (y en la mayoría de hostings), el disco NO es
# persistente entre despliegues ni reinicios — es decir, las fotos guardadas
# aquí se PERDERÁN cada vez que se vuelva a desplegar la app. Esto sirve
# solo para probar en tu PC o para pruebas rápidas en Render.
#
# Cuando tengas la cuenta de Cloudflare R2 lista, solo hay que reemplazar
# el contenido de la función `guardar_fotos()` de abajo por el código que
# suba cada archivo a tu bucket de R2 y devuelva la URL pública de cada uno.
# El resto del endpoint /registrar no necesita cambios.

CARPETA_FOTOS = "static/fotos_clientes"
os.makedirs(CARPETA_FOTOS, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


def guardar_fotos(fotos: List[UploadFile]) -> List[str]:
    """Guarda las fotos recibidas en disco local y devuelve sus URLs relativas.

    Reemplazar esta función por la subida a Cloudflare R2 cuando esté lista
    la cuenta. La firma (recibe una lista de UploadFile, devuelve una lista
    de URLs en texto) puede quedarse igual.
    """
    urls_guardadas = []

    for foto in fotos:
        if not foto.filename:
            # El input de fotos puede llegar "vacío" si no se seleccionó nada
            continue

        extension = os.path.splitext(foto.filename)[1]
        nombre_unico = f"{uuid.uuid4()}{extension}"
        ruta_destino = os.path.join(CARPETA_FOTOS, nombre_unico)

        with open(ruta_destino, "wb") as archivo_destino:
            archivo_destino.write(foto.file.read())

        urls_guardadas.append(f"/{ruta_destino}")

    return urls_guardadas


@app.get("/", response_class=HTMLResponse)
def mostrar_formulario(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/registrar", response_class=HTMLResponse)
def registrar_usuario(
    request: Request,
    # Datos personales
    primer_nombre: str = Form(...),
    segundo_nombre: Optional[str] = Form(None),
    primer_apellido: str = Form(...),
    segundo_apellido: Optional[str] = Form(None),
    dni_actual: str = Form(...),
    # Contacto en España
    telefono_principal: str = Form(...),
    telefono_alternativo: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    telegram_user: Optional[str] = Form(None),
    telegram_chat_id: Optional[str] = Form(None),
    # Recogida en España
    direccion_recogida: str = Form(...),
    # Destinatario en Paraguay
    nombre_destinatario_py: str = Form(...),
    telefono_destinatario_py: str = Form(...),
    direccion_destino_py: str = Form(...),
    # Notas y fotos
    notas: Optional[str] = Form(None),
    fotos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    urls_fotos = guardar_fotos(fotos)

    # NOTA: el modelo Cliente todavía no tiene una columna para guardar
    # las URLs de las fotos (solo el modelo Envio tiene `fotos_urls`).
    # Por ahora las fotos se guardan en disco pero su URL no queda asociada
    # al cliente en la base de datos. Avísame si quieres que agregue una
    # columna `fotos_urls` a Cliente, o que estas fotos se asocien a un
    # Envio creado junto con el cliente.

    nuevo_cliente = Cliente(
        primer_nombre=primer_nombre,
        segundo_nombre=segundo_nombre,
        primer_apellido=primer_apellido,
        segundo_apellido=segundo_apellido,
        dni_actual=dni_actual,
        telefono_principal=telefono_principal,
        telefono_alternativo=telefono_alternativo,
        email=email,
        telegram_user=telegram_user,
        telegram_chat_id=telegram_chat_id,
        direccion_recogida=direccion_recogida,
        nombre_destinatario_py=nombre_destinatario_py,
        telefono_destinatario_py=telefono_destinatario_py,
        direccion_destino_py=direccion_destino_py,
        notas=notas,
    )

    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)

    mensaje_exito = f"¡{primer_nombre} {primer_apellido} guardado con éxito en PostgreSQL!"
    if urls_fotos:
        mensaje_exito += f" ({len(urls_fotos)} foto(s) guardada(s) localmente)"

    return templates.TemplateResponse(
        request,
        name="index.html",
        context={"mensaje": mensaje_exito},
    )