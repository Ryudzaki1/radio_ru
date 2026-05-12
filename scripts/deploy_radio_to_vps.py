import io
import os
import tarfile
import time
from pathlib import Path

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
REMOTE_DIR = os.environ.get("REMOTE_DIR", "/opt/ai-chill-radio")
PUBLIC_URL = os.environ.get("PUBLIC_RADIO_URL", f"http://{HOST}")
ROOT = Path(__file__).resolve().parents[1]

INCLUDE = [
    "assets",
    "bot",
    "music",
    "src",
    ".dockerignore",
    ".env",
    ".env.example",
    "admin.html",
    "admin.js",
    "docker-compose.yml",
    "Dockerfile",
    "Dockerfile.quick-tunnel",
    "index.html",
    "package.json",
    "PUBLIC_ACCESS.md",
    "README.md",
    "script.js",
    "server.js",
    "styles.css",
]


def filter_env(data: bytes) -> bytes:
    lines = data.decode("utf-8", errors="replace").splitlines()
    out = []
    seen_port = False
    seen_public = False
    for line in lines:
        if line.startswith("PORT="):
            out.append("PORT=80")
            seen_port = True
        elif line.startswith("PUBLIC_RADIO_URL="):
            out.append(f"PUBLIC_RADIO_URL={PUBLIC_URL}")
            seen_public = True
        else:
            out.append(line)
    if not seen_port:
        out.append("PORT=80")
    if not seen_public:
        out.append(f"PUBLIC_RADIO_URL={PUBLIC_URL}")
    return ("\n".join(out) + "\n").encode("utf-8")


def build_archive() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for rel in INCLUDE:
            path = ROOT / rel
            if not path.exists():
                continue
            if path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file():
                        arcname = child.relative_to(ROOT).as_posix()
                        tar.add(child, arcname=arcname)
            elif rel == ".env":
                data = filter_env(path.read_bytes())
                info = tarfile.TarInfo(".env")
                info.size = len(data)
                info.mtime = int(time.time())
                info.mode = 0o600
                tar.addfile(info, io.BytesIO(data))
            else:
                tar.add(path, arcname=rel)
    return buffer.getvalue()


def run(client, command, timeout=900):
    print(f"--- {command}")
    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out.encode("ascii", errors="replace").decode("ascii"))
    if err:
        print(err.encode("ascii", errors="replace").decode("ascii"))
    if code:
        raise RuntimeError(f"command failed ({code}): {command}")


archive = build_archive()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    HOST,
    username=USER,
    password=PASSWORD,
    look_for_keys=False,
    allow_agent=False,
)

try:
    sftp = client.open_sftp()
    remote_archive = "/tmp/ai-chill-radio.tar.gz"
    with sftp.file(remote_archive, "wb") as fh:
        fh.write(archive)
    sftp.close()

    run(client, "export DEBIAN_FRONTEND=noninteractive; apt-get update; apt-get install -y ca-certificates curl gnupg")
    run(client, "command -v docker >/dev/null 2>&1 || (install -m 0755 -d /etc/apt/keyrings && curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc && chmod a+r /etc/apt/keyrings/docker.asc && . /etc/os-release && echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable\" > /etc/apt/sources.list.d/docker.list && apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)")
    run(client, f"mkdir -p {REMOTE_DIR}")
    run(client, f"tar -xzf {remote_archive} -C {REMOTE_DIR}")
    run(client, "ufw allow 80/tcp || true")
    run(client, f"cd {REMOTE_DIR} && docker compose up -d --build", timeout=1200)
    run(client, "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'")
    run(client, "curl -4 -I --max-time 10 http://127.0.0.1/ || true")
finally:
    client.close()
