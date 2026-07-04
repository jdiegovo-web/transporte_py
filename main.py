from fastapi import FastAPI, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

# Importamos las herramientas de tu paquete 'app'
from app.database import get_db
from app.models import Cliente  

app = FastAPI()
templates = Jinja2Templates(directory="templates")
templates.env.cache = None

@app.get("/", response_class=HTMLResponse)
def mostrar_formulario(request: Request):
    return templates.TemplateResponse(request, name="index.html")
    #return templates.TemplateResponse("index.html", {"request": request})

@app.post("/registrar", response_class=HTMLResponse)
def registrar_usuario(
    request: Request, 
    primer_nombre: str = Form(...), 
    segundo_nombre: Optional[str] = Form(None), 
    primer_apellido: str = Form(...), 
    segundo_apellido: Optional[str] = Form(None), 
    db: Session = Depends(get_db)
):
    # Rellenamos los campos obligatorios con valores fijos para la prueba
    nuevo_usuario = Cliente(
        # 1. Campos dinámicos desde la página web
        # izquierda variables de la BD y la derecha el input de la web
        primer_nombre=primer_nombre,
        segundo_nombre=segundo_nombre,
        primer_apellido=primer_apellido,
        segundo_apellido=segundo_apellido,

        # 2. Campos obligatorios de tu modelo rellenados para simulación
        dni_actual="00000000X",
        telefono_principal="000000000",
        direccion_recogida="Dirección de prueba 123",
        nombre_destinatario_py="Destinatario Prueba",
        telefono_destinatario_py="000000000",
        direccion_destino_py="Dirección Paraguay Prueba"
    )
    
    # Intentamos guardar en PostgreSQL
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    mensaje_exito = f"¡{primer_nombre} {primer_apellido} guardado con éxito en PostgreSQL!"
    return templates.TemplateResponse(
        request, 
        name="index.html", 
        context={"mensaje": mensaje_exito}
        #"index.html", 
        #{"request": request, "mensaje": mensaje_exito}
    )
