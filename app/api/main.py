from fastapi import FastAPI, UploadFile, Form, Request, Response, Cookie, Depends
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    StreamingResponse,
    RedirectResponse,
)

from fastapi.templating import Jinja2Templates

from typing import Optional
import os
import json

from app.db.crud import (
    get_all_schemas,
    get_schema_by_id,
    get_user,
    init_db,
    save_schema_by_id,
)
from app.services.mini import S3BucketService
from app.core.hash import get_password_hash, verify_password
from app.services.parser import process_upload_logic, itemlist

init_db(os.getenv("admin_user"), get_password_hash(os.getenv("admin_password")))

app = FastAPI()
templates = Jinja2Templates(directory="client")
minio_handler = S3BucketService(
    minio_endpoint=os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ROOT_USER"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD"),
    bucket=os.getenv("MINIO_BUCKET_NAME"),
    secure=False,
)


async def get_current_user(session_user: Optional[str] = Cookie(None)):
    if not session_user:
        return RedirectResponse(url="/login?error=unauthorized", status_code=303)
    return session_user


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@app.post("/loginuser")
async def login(username: str = Form(...), password: str = Form(...)):
    user = get_user(username)

    if user and verify_password(password, user.hash):
        response = Response(headers={"HX-Redirect": "/"})
        response.set_cookie(key="session_user", value=username, httponly=True)
        print(f"Пользователь {username} вошел")
        return response
    return HTMLResponse("<p style='color:red;'>Неверный логин или пароль</p>")


@app.get("/exit")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session_user", path="/")
    return response


@app.get("/")
async def index(user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    return FileResponse("client/index.html")


@app.get("/update", response_class=HTMLResponse)
async def get_update_page(request: Request, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    schemas = get_all_schemas()
    return templates.TemplateResponse(
        request=request, name="update.html", context={"schemas": schemas}
    )


@app.get("/edit/{schema_id}", response_class=HTMLResponse)
async def update_json(request: Request, schema_id: str, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    schema = get_schema_by_id(schema_id)
    metadata = json.dumps(schema.metadata_json, ensure_ascii=False, indent=4)
    return templates.TemplateResponse(
        request, "edit.html", {"schema": schema, "metadata_pretty": metadata}
    )


@app.get("/download", response_class=HTMLResponse)
async def get_download_page(request: Request, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    schemas = get_all_schemas()
    return templates.TemplateResponse(
        request=request, name="download.html", context={"schemas": schemas}
    )


@app.get("/download/{schema_id}")
async def download_json(schema_id: str, user=Depends(get_current_user)):
    if isinstance(user, RedirectResponse):
        return user
    schema = get_schema_by_id(schema_id)
    name = schema.filename
    headers = {"Content-Disposition": f'attachment; filename="{name}"'}
    return StreamingResponse(
        headers=headers,
        content=minio_handler.download_file(name),
        media_type="application/octet-stream",
    )


@app.post("/upload", response_class=HTMLResponse)
async def upload_file(
    file: UploadFile,
    schema_id: Optional[str] = Form(None),
    from_date: Optional[str] = Form(None),
    to_date: Optional[str] = Form(None),
    alias: Optional[str] = Form(None),
    user=Depends(get_current_user),
):
    if isinstance(user, RedirectResponse):
        return user

    # Вся логика вынесена в parser.py
    return await process_upload_logic(
        file, schema_id, from_date, to_date, alias, minio_handler
    )


@app.post("/save/{schema_id}", response_class=HTMLResponse)
async def save_json(
    request: Request,
    schema_id: str,
    metadata_str: str = Form(..., alias="metadata"),
    user=Depends(get_current_user),
):
    if isinstance(user, RedirectResponse):
        return user
    try:
        metadata_json = json.loads(metadata_str)
        metadata_valid = itemlist(**metadata_json)

        operation = save_schema_by_id(metadata_valid.model_dump(mode="json"), schema_id)
        print(operation)

        return Response(headers={"HX-Refresh": "true"})
    except Exception as e:
        return HTMLResponse(f"<p style='color:red;'>Ошибка сохранения: {e}</p>")
