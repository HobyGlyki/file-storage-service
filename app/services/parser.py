from zipfile import ZipFile
from io import BytesIO
import json
from datetime import date, datetime
from pydantic import BaseModel, field_validator, ValidationError
from fastapi import UploadFile

from app.db.crud import upload


class itemlist(BaseModel):
    from_date: date
    to_date: date
    xsd: str
    alias: str

    @field_validator("from_date", "to_date", mode="before")
    def parse_time(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%d.%m.%Y").date()
            except ValueError:
                pass
            try:
                return datetime.fromisoformat(v).date()
            except ValueError:
                raise ValueError(
                    f"Неверный формат даты: {v}. Ожидается ДД.ММ.ГГГГ или ГГГГ-ММ-ДД"
                )


class schemalist(BaseModel):
    tastes: dict[str, itemlist]


# основная функция
async def process_upload_logic(
    file: UploadFile,
    schema_id: str | None,
    from_date: str | None,
    to_date: str | None,
    alias: str | None,
    minio_handler,
):

    if file.filename.endswith("zip"):
        return await zip_upload(file, minio_handler)

    elif file.filename.endswith("xsd"):
        if schema_id is None:
            return "<p>Заполните ID файла</p>"
        return await xsd_upload(
            file, minio_handler, schema_id, from_date, to_date, alias
        )
    else:
        return "<p>неверный тип файла, загрузите xsd или zip с json файлом </p>"


# Сохранение файла в DB и в MiniO.
def upload_single_item(
    filename: str,
    file_stream,
    file_size: int,
    item_data: dict,
    schema_id: str,
    minio_handler,
):

    murl = minio_handler.upload_file(filename, file_stream, file_size)
    # Вызываем твою оригинальную функцию БД
    operation_result = upload(filename, filename[-3:], murl, item_data, schema_id)
    return operation_result


# Загрузка из Архива
async def zip_upload(file: UploadFile, minio_handler):
    try:
        byte_data = await file.read()
        zfiledata = BytesIO(byte_data)

        with ZipFile(zfiledata, "r") as myzip:
            ziplist = myzip.namelist()

            # 1. Сканируем архив
            jsonfile, other_files = scan_zip_contents(ziplist)
            if not jsonfile:
                return (
                    "<p>невернывй тип файла, загрузити xsd или zip с json файлом </p>"
                )

            # 2. Читаем JSON
            resultjson = json.loads(myzip.read(jsonfile))
            data = schemalist(tastes=resultjson)

            # 3. Обрабатываем элементы
            add_file, operation, not_in_zip = process_zip_items(
                data, myzip, ziplist, minio_handler
            )

            # 4. Вычисляем файлы, которые есть в архиве, но нет в JSON
            not_in_json = list(set(other_files) - set(add_file))

            # 5. Возвращаем красивый HTML отчет
            return generate_html_report(add_file, operation, not_in_zip, not_in_json)

    except Exception as e:
        return f"<p> ошибка загрузки файла: {str(e)[:40]}</p>"


# Загрузка единичного XSD
async def xsd_upload(
    file: UploadFile,
    minio_handler,
    schema_id: str,
    from_date: str,
    to_date: str,
    alias: str,
):
    try:
        jsonxsd = itemlist(
            from_date=from_date, to_date=to_date, xsd=file.filename, alias=alias
        )

        # Переиспользуем нашу функцию одиночной загрузки!
        upload_single_item(
            filename=file.filename,
            file_stream=file.file,
            file_size=file.size,
            item_data=jsonxsd.model_dump(mode="json"),
            schema_id=schema_id,
            minio_handler=minio_handler,
        )
        return f"<p> файл xsd:{file.filename}</p>"

    except ValidationError as e:
        return f"<p style='color:red;'>Ошибка валидации данных! {str(e)}.</p>"


# Загрузка из Архива
def process_zip_items(data: schemalist, myzip: ZipFile, ziplist: list, minio_handler):
    operation = []
    add_file = []
    not_in_zip = []

    for name, item in data.tastes.items():
        if item.xsd in ziplist:
            # Читаем конкретный файл из архива
            with myzip.open(item.xsd) as file_stream:
                file_size = myzip.getinfo(item.xsd).file_size

                # Передаем этот файл в функцию одиночной загрузки
                update_msg = upload_single_item(
                    filename=item.xsd,
                    file_stream=file_stream,
                    file_size=file_size,
                    item_data=item.model_dump(mode="json"),
                    schema_id=name,
                    minio_handler=minio_handler,
                )

            add_file.append(item.xsd)
            operation.append(update_msg)
        else:
            not_in_zip.append(item.xsd)

    return add_file, operation, not_in_zip


# Проверка в zip
def scan_zip_contents(ziplist: list):
    jsonfile = None
    other_files = []

    for f in ziplist:
        if f.endswith("json"):
            jsonfile = f
        else:
            other_files.append(f)

    return jsonfile, other_files


# генерация html ответа
def generate_html_report(
    add_file: list, operation: list, not_in_zip: list, not_in_json: list
):
    add_file_text = "".join(
        f"<li>{operation[n]}:{f}</li>" for n, f in enumerate(add_file)
    )
    not_in_zip_text = "".join(f"<li>{f}</li>" for f in not_in_zip)
    not_in_json_text = "".join(f"<li>{f}</li>" for f in not_in_json)

    add_p = (
        f"<p> Операция оконченна успешна: </p><ul> {add_file_text} </ul>"
        if add_file
        else "<p> ошибка добавления файла </p>"
    )
    notzip_p = (
        f"<p>Файлы отсутсвуют в Zip:</p> <ul> {not_in_zip_text}</ul>"
        if not_in_zip
        else ""
    )
    notjson_p = (
        f"<p>Файлы отсутсвуют в json: </p> <ul> {not_in_json_text}</ul>"
        if not_in_json
        else ""
    )

    return add_p + notzip_p + notjson_p
