from fastapi import FastAPI, File, UploadFile
from serverlogic.database import *
from fastapi.responses import FileResponse, HTMLResponse
from datetime import date, datetime
from zipfile import ZipFile
from io import BytesIO
import json
from pydantic import BaseModel, field_validator
from typing import List


init_db()

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
        print(True)

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
            for name, item in data.tastes.items():
                print((item.to_date))
                if item.xsd in ziplist:
                    print(myzip.open(item.xsd))
            return f'<p>Файлы что хранятся:{str(result)} </p> <p>json файл:{jsonfile} </p>'
        
    if file.filename[-3:] == "xsd":
        return f'<p> файл xsd:{file.filename}</p>'
    else:
        return f'<p>невернывй тип файла, загрузити xsd или zip с json файлом </p>'