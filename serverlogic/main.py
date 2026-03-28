from fastapi import FastAPI, File, UploadFile
from serverlogic.database import *
from fastapi.responses import FileResponse, HTMLResponse
import os
from zipfile import ZipFile
from io import BytesIO
import json

init_db()

app = FastAPI()

@app.get("/")
async def index():
    return FileResponse('client/index.html')

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
            for f in myzip.namelist(): 
                if  f[-4:] == "json":
                    jsonfile = f
                else:
                    result.append(f)

            if not jsonfile:
                return f'<p>невернывй тип файла, загрузити XLS или zip с json файлом </p>'
            
            resultjson = json.loads(myzip.read(jsonfile))
            print(resultjson)
            return f'<p>Файлы что хранятся:{str(result)} </p> <p>json файл:{jsonfile} </p>'
        
    if file.filename[-3:] == "xsd":
        return f'<p> файл xsd:{file.filename}</p>'
    else:
        return f'<p>невернывй тип файла, загрузити xsd или zip с json файлом </p>'