from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "api is running"}

@app.get("/hello-world")
async def root():
    return {"message": "Hello World"}