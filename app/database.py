from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
# sqlalchemy.url = postgresql+psycopg2://postgres:postgres123@localhost:5432/transportes_py


DATABASE_URL = "postgresql+psycopg://neondb_owner:npg_xJc5P0vSVMNh@ep-morning-heart-atoqolhi-pooler.c-9.us-east-1.aws.neon.tech/transporte_limpio?sslmode=require&channel_binding=require"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()