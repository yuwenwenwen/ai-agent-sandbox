
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