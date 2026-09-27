
import uuid
import docker

IMAGE = "python:3.12-slim"
LABEL = "ai-agent-sandbox"


def get_docker_client():
    return docker.from_env()


def create_sandbox():
    client = get_docker_client()
    sandbox_id = str(uuid.uuid4())

    container = client.containers.run(
        IMAGE,
        command="sleep infinity",
        name=f"sandbox-{sandbox_id}",
        detach=True,
        working_dir="/workspace",
        network_disabled=True,
        mem_limit="256m",
        nano_cpus=500_000_000,
        cap_drop=["ALL"],
        security_opt=["no-new-privileges"],
        pids_limit=64,
        labels={"app": LABEL},
    )

    return {
        "id": sandbox_id,
        "container_id": container.id,
        "status": "running",
    }


def list_sandboxes():
    client = get_docker_client()

    containers = client.containers.list(
        all=True,
        filters={"label": f"app={LABEL}"},
    )

    return [
        {
            "id": c.name.removeprefix("sandbox-"),
            "container_id": c.id,
            "status": c.status,
        }
        for c in containers
    ]


def delete_sandbox(sandbox_id: str):
    client = get_docker_client()
    container = client.containers.get(
        f"sandbox-{sandbox_id}"
    )

    if container.labels.get("app") != LABEL:
        raise ValueError("Not a managed sandbox")

    container.remove(force=True)

    return {
        "id": sandbox_id,
        "status": "deleted",
    }

import re
import subprocess

def execute_python(sandbox_id: str, code: str):
    # 確認 Sandbox ID 格式
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", sandbox_id):
        raise ValueError("Invalid sandbox ID")

    if not code.strip() or len(code) > 4096:
        raise ValueError("Code must be 1–4096 characters")

    client = get_docker_client()
    container = client.containers.get(
        f"sandbox-{sandbox_id}"
    )

    # 避免操作不屬於本專案的容器
    if container.labels.get("app") != LABEL:
        raise ValueError("Not a managed sandbox")

    if container.status != "running":
        raise ValueError("Sandbox is not running")

    # 使用容器內的 timeout 限制 Python 執行時間
    result = subprocess.run(
        [
            "docker", "exec",
            "-w", "/workspace",
            container.id,
            "timeout", "-s", "KILL", "5s",
            "python", "-c", code,
        ],
        capture_output=True,
        text=True,
        timeout=8,
    )

    return {
        "sandbox_id": sandbox_id,
        "exit_code": result.returncode,
        "stdout": result.stdout[:10000],
        "stderr": result.stderr[:10000],
    }

def list_sandbox_files(sandbox_id: str):
    client = get_docker_client()

    container = client.containers.get(
        f"sandbox-{sandbox_id}"
    )

    if container.labels.get("app") != LABEL:
        raise ValueError("Not a managed sandbox")

    if container.status != "running":
        raise ValueError("Sandbox is not running")

    result = container.exec_run(
        ["python", "-c",
         "import os, json; "
         "print(json.dumps(sorted(os.listdir('/tmp'))))"],
        demux=True,
    )

    if result.exit_code != 0:
        raise RuntimeError("Failed to list files")

    stdout, _ = result.output

    import json
    return {
        "sandbox_id": sandbox_id,
        "files": json.loads(stdout.decode("utf-8")),
    }

def _managed_running_container(sandbox_id: str):
    # UUID validation prevents selecting arbitrary Docker container names.
    uuid.UUID(sandbox_id)
    if str(uuid.UUID(sandbox_id)) != sandbox_id:
        raise ValueError("Invalid sandbox ID")
    container = get_docker_client().containers.get(f"sandbox-{sandbox_id}")
    if container.labels.get("app") != LABEL:
        raise ValueError("Not a managed sandbox")
    if container.status != "running":
        raise ValueError("Sandbox is not running")
    return container


def upload_sandbox_file(sandbox_id: str, filename: str, content: bytes):
    import io
    import tarfile
    from pathlib import PurePath

    if not filename or filename in (".", "..") or PurePath(filename).name != filename:
        raise ValueError("Invalid filename")
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,99}", filename):
        raise ValueError("Filename must use letters, numbers, dots, hyphens or underscores")
    if not filename.lower().endswith((".csv", ".txt", ".json", ".py")):
        raise ValueError("Only CSV, TXT, JSON and Python files are allowed")
    if len(content) > 5 * 1024 * 1024:
        raise ValueError("File exceeds 5 MB")

    container = _managed_running_container(sandbox_id)
    # This folder is created inside the selected container only.
    setup = container.exec_run(["mkdir", "-p", "/workspace"])
    if setup.exit_code != 0:
        raise RuntimeError("Cannot create sandbox workspace")

    # Do not overwrite an existing file. No host bind mount or shared volume.
    exists = container.exec_run(["test", "-e", f"/workspace/{filename}"])
    if exists.exit_code == 0:
        raise FileExistsError("File already exists in this sandbox")
    if exists.exit_code != 1:
        raise RuntimeError("Cannot inspect sandbox workspace")

    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        info = tarfile.TarInfo(name=filename)
        info.size = len(content)
        info.mode = 0o600
        tar.addfile(info, io.BytesIO(content))
    archive.seek(0)
    if not container.put_archive("/workspace", archive):
        raise RuntimeError("Upload to sandbox failed")
    return {"sandbox_id": sandbox_id, "filename": filename, "path": f"/workspace/{filename}"}


def list_workspace_files(sandbox_id: str):
    import json
    container = _managed_running_container(sandbox_id)
    result = container.exec_run([
        "python", "-c",
        "import os,json; os.makedirs('/workspace',exist_ok=True); "
        "print(json.dumps(sorted(n for n in os.listdir('/workspace') "
        "if os.path.isfile(os.path.join('/workspace',n)))))"
    ], demux=True)
    if result.exit_code != 0:
        raise RuntimeError("Failed to list workspace files")
    stdout, _ = result.output
    return {"sandbox_id": sandbox_id, "files": json.loads(stdout.decode("utf-8"))}
