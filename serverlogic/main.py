from fastapi import FastAPI, File, UploadFile
from serverlogic.database import *
from fastapi.responses import FileResponse, HTMLResponse

init_db()

app = FastAPI()

@app.get("/")
async def index():
    # Путь к HTML внутри папки Wikis
    return FileResponse('client/index.html')

@app.post('/upload', response_class=HTMLResponse)
async def upload_file(file: UploadFile):
    return f'<p>{str(file.filename)}</p>'

