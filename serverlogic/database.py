from sqlalchemy import Column, Integer, String, JSON, DateTime, create_engine, MetaData
from sqlalchemy.orm import sessionmaker, as_declarative
import datetime
import os

#для тестов в оперативной памяти
#DATABASE_URL = "sqlite:///:memory:"

DATABASE_URL =os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

@as_declarative() #декоратор для класса
class AbstractModel:
    id = Column(Integer, primary_key=True, autoincrement=True)
    test_time = Column(DateTime, default=datetime.datetime.utcnow) #для тестов проверка создания данных.

class Users(AbstractModel):
    __tablename__ = "Client"
    client_name = Column(String)
    hash = Column(String)

class FileServ(AbstractModel):
    __tablename__ = "Schemas"

    filename = Column(String)
    file_type = Column(String)
    minio_path = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow) 
    metadata_json = Column(JSON)


def init_db(): #инициализация таблицы.
    AbstractModel.metadata.create_all(bind=engine)


def timetest():
    db = SessionLocal()
    if not db.query(Users).first():
        new_table = Users()
        db.add(new_table)
        db.commit()
    
    result = db.query(Users).first()
    db.close()
    return result

# print(timetest().test_time)

    

def localtest():
    init_db()

    db = SessionLocal()

    new_user = Users(
            client_name="Тест",
            hash="ХэшТест"
        )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    print(new_user.id)
