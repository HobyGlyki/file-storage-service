from fastapi import FastAPI, File, UploadFile, Form, Request, Response
from serverlogic.database import *
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
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
templates = Jinja2Templates(directory="client")




@app.get("/")
async def index():
    return FileResponse('client/index.html')

@app.get("/update", response_class=HTMLResponse)
async def get_update_page(request: Request):
    schemas = get_all_schemas()
    return templates.TemplateResponse(request= request, name= "update.html", context={"schemas": schemas})

@app.get('/edit/{schema_id}', response_class =HTMLResponse)
async def update_json(request: Request, schema_id:str):
    schema = get_schema_by_id(schema_id)
    metadata = json.dumps(schema.metadata_json, ensure_ascii=False, indent=4)
    return templates.TemplateResponse(request, 'edit.html', {"schema": schema, "metadata_pretty": metadata})

@app.get("/download", response_class=HTMLResponse)
async def get_update_page(request: Request):
    schemas = get_all_schemas()
    return templates.TemplateResponse(request= request, name= "download.html", context={"schemas": schemas})

@app.get('/download/{schema_id}')
async def update_json(schema_id:str):
    schema = get_schema_by_id(schema_id)
    name = schema.filename
    headers = {
        'Content-Disposition': f'attachment; filename="{name}"'
    }
    return StreamingResponse(headers= headers, content= minio_handler.download_file(name), media_type='application/octet-stream', )



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
                 pass
            try:
                return datetime.fromisoformat(v).date()
            except ValueError:
                raise ValueError(f"Неверный формат даты: {v}. Ожидается ДД.ММ.ГГГГ или ГГГГ-ММ-ДД")

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
        
            jsonxsd = itemlist(from_date=from_date, 
                               to_date=to_date, 
                               xsd=file.filename, 
                               alias=alias)
            Murl = minio_handler.upload_file(file.filename, file.file, file.size)
            upload(file.filename, file.filename[-3], Murl, jsonxsd.model_dump(mode='json'), schema_id=schema_id)
            return f'<p> файл xsd:{file.filename}</p>'
        except ValidationError as e: return f"<p style='color:red;'>Ошибка валидации данных! {str(e) }.</p>"
    else:
        return f'<p>невернывй тип файла, загрузити xsd или zip с json файлом </p>'
    

@app.post('/save/{schema_id}', response_class=HTMLResponse)
async def save_json(
    request: Request,
    schema_id: str,
    metadata_str: str=Form(..., alias="metadata")):
    try:
        metadata_json = json.loads(metadata_str)
        metadata_valid = itemlist(**metadata_json)

        operation = save_schema_by_id(metadata_valid.model_dump(mode='json'), schema_id)
        print(operation)
        
        return Response(headers={"HX-Refresh": "true"})
    except Exception as e:
        print(e)