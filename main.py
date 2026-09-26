
from fastapi import FastAPI, HTTPException
from docker.errors import DockerException, NotFound
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from subprocess import TimeoutExpired



from sandbox_manager import (
    create_sandbox,
    list_sandboxes,
    delete_sandbox,
    execute_python,
)

app = FastAPI(title="AI Agent Sandbox")


@app.get("/")
def home():
    return {"message": "AI Agent Sandbox is running!"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sandboxes")
def create():
    try:
        return create_sandbox()
    except DockerException:
        raise HTTPException(
            status_code=503,
            detail="Docker service unavailable",
        )


@app.get("/sandboxes")
def list_all():
    try:
        return list_sandboxes()
    except DockerException:
        raise HTTPException(
            status_code=503,
            detail="Docker service unavailable",
        )

@app.get("/ui")
def frontend():
    return FileResponse("static/index.html")


@app.delete("/sandboxes/{sandbox_id}")
def delete(sandbox_id: str):
    try:
        return delete_sandbox(sandbox_id)
    except NotFound:
        raise HTTPException(
            status_code=404,
            detail="Sandbox not found",
        )
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Invalid sandbox",
        )
    except DockerException:
        raise HTTPException(
            status_code=503,
            detail="Docker service unavailable",
        )

class ExecuteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=4096)


@app.post("/sandboxes/{sandbox_id}/execute")
def execute(sandbox_id: str, request: ExecuteRequest):
    try:
        return execute_python(sandbox_id, request.code)

    except NotFound:
        raise HTTPException(
            status_code=404,
            detail="Sandbox not found",
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Execution timed out",
        )

    except DockerException:
        raise HTTPException(
            status_code=503,
            detail="Docker service unavailable",
        )