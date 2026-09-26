
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