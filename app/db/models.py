from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from sqlalchemy.orm import as_declarative


@as_declarative()
class AbstractModel:
    id = Column(Integer, primary_key=True, autoincrement=True)


class Users(AbstractModel):
    __tablename__ = "Client"
    client_name = Column(String)
    hash = Column(String)
    access_level = Column(Integer, default=1)


class FileServ(AbstractModel):
    __tablename__ = "Schemas"
    filename = Column(String)
    file_type = Column(String)
    minio_path = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    last_update_at = Column(DateTime, default=datetime.now)
    metadata_json = Column(JSON)
    schema_id = Column(String, unique=True)
