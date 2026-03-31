from fastapi import FastAPI, File, UploadFile, Form
from serverlogic.database import *
from fastapi.responses import FileResponse, HTMLResponse
from datetime import date, datetime
from zipfile import ZipFile
from io import BytesIO
import json
from pydantic import BaseModel, field_validator, ValidationError
from typing import List, Optional
from serverlogic.mini import S3BucketService


init_db()


minio_handler = S3BucketService(
    minio_endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    bucket=os.getenv("MINIO_BUCKET_NAME"),
    secure=False
)

app = FastAPI()

@app.get("/")
async def index():
    return FileResponse('client/index.html')

class itemlist(BaseModel):
    from_date: date
    to_date: date
    xsd: str
    alias: str

    @field_validator('from_date', 'to_date', mode="before")
    def parse_time(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%d.%m.%Y").date()
            except ValueError:
                raise ValueError(f"Неверный формат даты: {v}")


class schemalist(BaseModel):
    tastes: dict[str, itemlist]  
    

@app.post('/upload', response_class=HTMLResponse)
async def upload_file(
    file: UploadFile,
    schema_id: Optional[str] = Form(None),
    from_date: Optional[str] = Form(None),
    to_date: Optional[str] = Form(None),
    alias: Optional[str] = Form(None)
):
    #Zip файлы
    if file.filename[-3:] == "zip":

        result =[]
        jsonfile = None

        byte = await file.read()
        zfiledata = BytesIO(byte)
        
        with ZipFile(zfiledata, "r") as myzip:
            ziplist = myzip.namelist()
            for f in ziplist: 
                if  f[-4:] == "json":
                    jsonfile = f
                else:
                    result.append(f)

            if not jsonfile:
                return f'<p>невернывй тип файла, загрузити XLS или zip с json файлом </p>'
            try:
                resultjson = json.loads(myzip.read(jsonfile))
                data = schemalist(tastes=resultjson)
                names = list(data.tastes.keys())
                operation = []
                add_file = []
                not_in_zip = []
                for name, item in data.tastes.items():
                    if item.xsd in ziplist:
                        Murl = minio_handler.upload_file(item.xsd, myzip.open(item.xsd), myzip.getinfo(item.xsd).file_size)
                        update = upload(item.xsd, item.xsd[-3], Murl, item.model_dump(mode='json'), name) 
                        add_file.append(item.xsd)
                        operation.append(update)
                    else: not_in_zip.append(item.xsd)
                not_in_json = list(set(result) - set(add_file))

                add_file_text = "".join(f"<li>{operation[n]}:{file}</li>" for n, file in enumerate(add_file))
                not_in_zip_text = "".join(f"<li>{file}</li>" for file in not_in_zip)
                not_in_json_text = "".join(f"<li>{file}</li>" for file in not_in_json)
            
                if add_file: add_p = f"<p> Операция оконченна успешна: </p><ul> {add_file_text} </ul>"
                else: add_p = f"<p> ошибка добавления файла </p>"
                if not_in_zip: notzip_p= f'<p>Файлы отсутсвуют в Zip:</p> <ul> {str(not_in_zip_text)}</ul>'
                else: notzip_p = ''
                if not_in_json: notjson_p=f'<p>Файлы отсутсвуют в json: </p> <ul> {str(not_in_json_text)}</ul>'
                else: notjson_p = ''

                return add_p + notzip_p + notjson_p
            except Exception as e: return f"<p> ошибка загрузки файла: {e[:40]}</p>"
        
    if file.filename[-3:] == "xsd":
        if schema_id == None:
            return f'<p>Заполните ID файла</p>'
        try:
        
            jsonxsd = itemlist(from_date=datetime.strftime(datetime.fromisoformat(from_date).date(), "%d.%m.%Y"), 
                               to_date=datetime.strftime(datetime.fromisoformat(to_date).date(), "%d.%m.%Y"), 
                               xsd=file.filename, 
                               alias=alias)
            Murl = minio_handler.upload_file(file.filename, file.file, file.size)
            upload(file.filename, file.filename[-3], Murl, jsonxsd.model_dump(mode='json'), schema_id=schema_id)
            return f'<p> файл xsd:{file.filename}</p>'
        except ValidationError as e: return f"<p style='color:red;'>Ошибка валидации данных! {str(e) }.</p>"
    else:
        return f'<p>невернывй тип файла, загрузити xsd или zip с json файлом </p>'