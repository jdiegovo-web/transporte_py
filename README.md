# Plataforma de Transporte a Paraguay — Base de Datos

## Estructura del proyecto

```
transporte_py/
├── app/
│   ├── models/
│   │   └── __init__.py      ← Todos los modelos SQLAlchemy
│   ├── database.py          ← Configuración de conexión y sesión
│   └── utils.py             ← Funciones auxiliares (códigos, duplicados, historial)
├── alembic/
│   ├── env.py               ← Configuración de migraciones
│   └── versions/            ← Archivos de migración generados
├── alembic.ini              ← Configuración de Alembic
├── requirements.txt
└── .env.example             ← Copiar a .env y rellenar
```

## Puesta en marcha

### 1. Instalar dependencias

```bash
cd transporte_py
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tu usuario/contraseña de PostgreSQL
```

### 3. Crear la base de datos en PostgreSQL

```bash
psql -U postgres
CREATE DATABASE transporte_py;
\q
```

### 4. Crear la migración inicial y aplicarla

```bash
alembic revision --autogenerate -m "crear_tablas_iniciales"
alembic upgrade head
```

### 5. Verificar en pgAdmin

Conecta a `localhost:5432 / transporte_py` y deberías ver las tablas:
- `clientes`
- `historial_cambios_cliente`
- `contenedores`
- `envios`
- `pagos`

---

## Tablas y relaciones

```
clientes (1) ──────────── (N) envios
clientes (1) ──────────── (N) historial_cambios_cliente
contenedores (1) ──────── (N) envios
envios (1) ─────────────── (N) pagos
```

## Estados del envío

```
pendiente_recogida → recogido → en_almacen → asignado_contenedor
→ en_transito → llego_paraguay → en_distribucion → entregado
```

## Añadir campos nuevos (sin perder datos)

```bash
# 1. Editar el modelo en app/models/__init__.py
# 2. Generar migración automática
alembic revision --autogenerate -m "descripcion_del_cambio"
# 3. Aplicar
alembic upgrade head
```
