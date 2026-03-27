from fastapi import FastAPI
from serverlogic.database import *

init_db()

app = FastAPI()

@app.get("/")
async def index():
    # Путь к HTML внутри папки Wikis
    return timetest().test_time
