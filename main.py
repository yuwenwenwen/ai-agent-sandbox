
from fastapi import FastAPI

app = FastAPI(title="AI Agent Sandbox")


@app.get("/")
def home():
    return {"message": "AI Agent Sandbox is running!"}


@app.get("/health")
def health():
    return {"status": "ok"}