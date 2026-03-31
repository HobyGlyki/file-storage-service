from sqlalchemy import Column, Integer, String, JSON, DateTime, create_engine, MetaData
from sqlalchemy.orm import sessionmaker, as_declarative
from datetime import datetime
import os
import json

#для тестов в оперативной памяти
#DATABASE_URL = "sqlite:///:memory:"

DATABASE_URL =os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

@as_declarative() #декоратор для класса
class AbstractModel:
    id = Column(Integer, primary_key=True, autoincrement=True)

class Users(AbstractModel):
    __tablename__ = "Client"
    client_name = Column(String)
    hash = Column(String)

class FileServ(AbstractModel):
    __tablename__ = "Schemas"
    filename = Column(String)
    file_type = Column(String)
    minio_path = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    last_update_at = Column(DateTime, default=datetime.now) 
    metadata_json = Column(JSON)
    schema_id = Column(String, unique=True)


def init_db(): #инициализация таблицы.
    AbstractModel.metadata.create_all(bind=engine)


def upload(filename: str, file_type: str, minio_path: str, metadata_json:dict[str, any], schema_id: str):
    db = SessionLocal()   
    existing_file = db.query(FileServ).filter(FileServ.schema_id == schema_id).first()

    if existing_file:
        date = datetime.now()
        # Обновляем старую запись
        existing_file.filename = filename
        existing_file.file_type = file_type
        existing_file.minio_path = minio_path
        existing_file.metadata_json = metadata_json
        existing_file.last_update_at = date 
        db.commit()
        db.refresh(existing_file)
        db.close()
        return "База Данных обнавленна"
    new_file = FileServ(
        filename = filename,
        file_type = file_type,
        minio_path = minio_path,
        metadata_json = metadata_json,
        schema_id = schema_id
        )
    db.add(new_file)
    db.commit()
    db.close()
    return "База Данных Созданна"