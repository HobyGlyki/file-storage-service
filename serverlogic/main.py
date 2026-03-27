from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def index():
    # Путь к HTML внутри папки Wikis
    return "Hello World"
