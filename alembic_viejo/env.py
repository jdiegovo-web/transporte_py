import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.database import Base
import app.models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", "postgresql://postgres:postgres123@localhost:5432/transportes_py")

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # --- MODIFICA DESDE AQUÍ ---
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata
            )

            with context.begin_transaction():
                context.run_migrations()
    except Exception as e:
        print("\n" + "="*50)
        print("EL ERROR REAL DE POSTGRESQL ES:")
        import traceback
        # Buscamos el error original atrapado en el historial de excepciones
        exc_type, exc_value, exc_tb = traceback.sys.exc_info()
        orig_err = exc_value
        while orig_err.__cause__ or orig_err.__context__:
            orig_err = orig_err.__cause__ or orig_err.__context__
        
        # Si es un error de codificación, intentamos leer qué bytes causaron el fallo
        if isinstance(orig_err, UnicodeDecodeError):
            try:
                mensaje_real = orig_err.object.decode('cp1252', errors='replace')
                print(mensaje_real)
            except Exception:
                print(f"Error de decodificación en la posición {orig_err.start}. Bytes: {orig_err.object[orig_err.start:orig_err.end]}")
        else:
            print(str(e))
        print("="*50 + "\n")
        raise e

    # --- HASTA AQUÍ ---


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()