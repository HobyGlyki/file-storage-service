from fastapi import FastAPI, File, UploadFile
from serverlogic.database import *
from fastapi.responses import FileResponse, HTMLResponse
from datetime import date, datetime
from zipfile import ZipFile
from io import BytesIO
import json
from pydantic import BaseModel, field_validator
from typing import List
from serverlogic.mini import S3BucketService


init_db()


minio_handler = S3BucketService(
    minio_endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    bucket=os.getenv("MINIO_BUCKET_NAME"),
    secure=False
)
print(os.getenv("MINIO_ENDPOINT"))

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
async def upload_file(file: UploadFile):
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
            
            resultjson = json.loads(myzip.read(jsonfile))
            data = schemalist(tastes=resultjson)
            name = list(data.tastes.keys())
            add_file = []
            not_in_zip = []
            for name, item in data.tastes.items():
                if item.xsd in ziplist:
                    add_file.append(item.xsd)
                    minio_handler.upload_file(item.xsd, myzip.open(item.xsd), myzip.getinfo(item.xsd).file_size)
                else: not_in_zip.append(item.xsd)
            not_in_json = list(set(result) - set(add_file))
            
            if add_file: add_p = f"<p> Добавленны файла:{str(add_file)}</p>"
            else: add_p = f"<p> ошибка добавления файла </p>"
            if not_in_zip: notzip_p= f'<p>Файлы отсутсвуют в Zip:{str(not_in_zip)}</p>'
            else: notzip_p = ''
            if not_in_json: notjson_p=f'<p>Файлы отсутсвуют в json:{str(not_in_json)}</p>'
            else: notjson_p = ''

            return add_p + notzip_p + notjson_p
        
    if file.filename[-3:] == "xsd":
        print(minio_handler.upload_file(file.filename, file.file, file.size))
        return f'<p> файл xsd:{file.filename}</p>'
    else:
        return f'<p>невернывй тип файла, загрузити xsd или zip с json файлом </p>'