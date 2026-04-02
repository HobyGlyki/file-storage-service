from datetime import datetime
from app.db.database import SessionLocal
from app.db.models import Users, FileServ


def init_db(admin_user, admin_password):  # инициализация таблицы.
    # AbstractModel.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        exists = db.query(Users).filter(Users.client_name == admin_user).first()
        if not exists:
            new_admin = Users(client_name=admin_user, hash=admin_password)
            db.add(new_admin)
            db.commit()
            print(f"Администратор {admin_user} успешно создан.")
    except Exception as e:
        print(f"Ошибка при инициализации админа: {e}")
        db.rollback()
    finally:
        db.close()


def get_user(name):
    db = SessionLocal()
    schema = db.query(Users).filter(Users.client_name == name).first()
    db.close()
    return schema


def upload(
    filename: str,
    file_type: str,
    minio_path: str,
    metadata_json: dict[str, any],
    schema_id: str,
):
    db = SessionLocal()
    existing_file = db.query(FileServ).filter(FileServ.schema_id == schema_id).first()

    if existing_file:
        now_timestamp = datetime.now()
        # Обновляем старую запись
        existing_file.filename = filename
        existing_file.file_type = file_type
        existing_file.minio_path = minio_path
        existing_file.metadata_json = metadata_json
        existing_file.last_update_at = now_timestamp
        db.commit()
        db.refresh(existing_file)
        db.close()
        return "База Данных обнавленна"
    new_file = FileServ(
        filename=filename,
        file_type=file_type,
        minio_path=minio_path,
        metadata_json=metadata_json,
        schema_id=schema_id,
    )
    db.add(new_file)
    db.commit()
    db.close()
    return "База Данных Созданна"


def get_all_schemas():
    db = SessionLocal()
    schemas = db.query(FileServ).all()
    db.close()
    return schemas


def get_schema_by_id(schema_id: str):
    db = SessionLocal()
    schema = db.query(FileServ).filter(FileServ.schema_id == schema_id).first()
    db.close()
    return schema


def save_schema_by_id(metadata_json: dict[str, any], schema_id: str):
    db = SessionLocal()
    existing_file = db.query(FileServ).filter(FileServ.schema_id == schema_id).first()

    if existing_file:
        date = datetime.now()
        # Обновляем старую запись
        existing_file.metadata_json = metadata_json
        existing_file.last_update_at = date
        db.commit()
        db.refresh(existing_file)
        db.close()
        return "База Данных обнавленна"
    else:
        db.close()
        return "ошибка: Данной схемы не существует. "
