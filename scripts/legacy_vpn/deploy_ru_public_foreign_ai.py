import io
import os
import posixpath
import tarfile
import time
from pathlib import Path

import paramiko


ROOT = Path(__file__).resolve().parents[1]

RU_HOST = os.environ["RU_HOST"]
RU_USER = os.environ.get("RU_USER", "radio")
RU_KEY = os.environ["RU_KEY"]
DE_HOST = os.environ["DE_HOST"]
DE_USER = os.environ.get("DE_USER", "root")
DE_PASS = os.environ["DE_PASS"]
DOMAIN = os.environ.get("RADIO_DOMAIN", "radio.ryudzaki.website")
RU_DIR = os.environ.get("RU_DIR", "/opt/ai-chill-radio")
WG_PORT = os.environ.get("WG_PORT", "51820")

WG_DE_IP = "10.77.0.1"
WG_RU_IP = "10.77.0.2"

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


def load_key(path):
    for key_cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return key_cls.from_private_key_file(path)
        except paramiko.SSHException:
            continue
    raise RuntimeError(f"Could not read SSH key: {path}")


def connect_password(host, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, password=password, look_for_keys=False, allow_agent=False)
    return client


def connect_key(host, user, key_path):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, pkey=load_key(key_path), look_for_keys=False, allow_agent=False)
    return client


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
    return out


def sudo_script(client, script, timeout=900):
    command = "sudo -n bash -s"
    print("--- sudo bash -s")
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    stdin.write(script)
    stdin.channel.shutdown_write()
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out.encode("ascii", errors="replace").decode("ascii"))
    if err:
        print(err.encode("ascii", errors="replace").decode("ascii"))
    if code:
        raise RuntimeError(f"sudo script failed ({code})")
    return out


def filter_env(data):
    lines = data.decode("utf-8", errors="replace").splitlines()
    replacements = {
        "PORT": "127.0.0.1:3000",
        "PUBLIC_RADIO_URL": f"https://{DOMAIN}",
        "ELEVENLABS_BASE_URL": f"http://{WG_DE_IP}:18080",
    }
    seen = set()
    output = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in replacements:
            output.append(f"{key}={replacements[key]}")
            seen.add(key)
        else:
            output.append(line)
    for key, value in replacements.items():
        if key not in seen:
            output.append(f"{key}={value}")
    return ("\n".join(output) + "\n").encode("utf-8")


def build_archive():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for rel in INCLUDE:
            path = ROOT / rel
            if not path.exists():
                continue
            if path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file():
                        tar.add(child, arcname=child.relative_to(ROOT).as_posix())
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


def put_bytes(client, remote_path, data):
    sftp = client.open_sftp()
    with sftp.file(remote_path, "wb") as fh:
        fh.write(data)
    sftp.close()


def install_common_de(client, ru_public_key):
    script = f"""
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

systemctl stop xray || true
systemctl disable xray || true
systemctl stop caddy || true
docker compose -f /opt/ai-chill-radio/docker-compose.yml down --remove-orphans || true
docker rm -f ai-chill-radio ai-chill-radio-bot ai-chill-radio-tunnel ai-chill-radio-quick-tunnel 2>/dev/null || true
rm -rf /opt/ai-chill-radio /tmp/ai-chill-radio.tar.gz

apt-get update
apt-get install -y wireguard caddy ca-certificates curl

mkdir -p /etc/wireguard
chmod 700 /etc/wireguard
if [ ! -f /etc/wireguard/de_private.key ]; then
  umask 077
  wg genkey > /etc/wireguard/de_private.key
fi
DE_PRIVATE="$(cat /etc/wireguard/de_private.key)"

cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
Address = {WG_DE_IP}/24
ListenPort = {WG_PORT}
PrivateKey = $DE_PRIVATE

[Peer]
PublicKey = {ru_public_key}
AllowedIPs = {WG_RU_IP}/32
EOF

ufw allow {WG_PORT}/udp || true
systemctl enable wg-quick@wg0
systemctl restart wg-quick@wg0

cat > /etc/caddy/Caddyfile <<'EOF'
http://{WG_DE_IP}:18080 {{
    bind {WG_DE_IP}
    reverse_proxy https://api.elevenlabs.io {{
        header_up Host api.elevenlabs.io
        header_up X-Forwarded-Host api.elevenlabs.io
    }}
}}
EOF

systemctl enable caddy
systemctl restart caddy
systemctl is-active wg-quick@wg0
systemctl is-active caddy
wg show
"""
    sudo_script(client, script, timeout=900)


def install_ru(client, archive, de_public_key):
    remote_archive = "/tmp/ai-chill-radio.tar.gz"
    put_bytes(client, remote_archive, archive)
    script = f"""
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates curl gnupg wireguard caddy

if ! command -v docker >/dev/null 2>&1; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${{VERSION_CODENAME}} stable" > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

mkdir -p /etc/wireguard
chmod 700 /etc/wireguard
if [ ! -f /etc/wireguard/ru_private.key ]; then
  umask 077
  wg genkey > /etc/wireguard/ru_private.key
fi
RU_PRIVATE="$(cat /etc/wireguard/ru_private.key)"

cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
Address = {WG_RU_IP}/24
PrivateKey = $RU_PRIVATE

[Peer]
PublicKey = {de_public_key}
Endpoint = {DE_HOST}:{WG_PORT}
AllowedIPs = {WG_DE_IP}/32
PersistentKeepalive = 25
EOF

systemctl enable wg-quick@wg0
systemctl restart wg-quick@wg0

mkdir -p {RU_DIR}
tar -xzf {remote_archive} -C {RU_DIR}
chown -R root:root {RU_DIR}

cd {RU_DIR}
docker compose up -d --build

cat > /etc/caddy/Caddyfile <<'EOF'
:80 {{
    encode gzip zstd
    reverse_proxy 127.0.0.1:3000
}}

{DOMAIN} {{
    encode gzip zstd
    reverse_proxy 127.0.0.1:3000
}}
EOF

ufw allow 80/tcp || true
ufw allow 443/tcp || true
systemctl enable caddy
systemctl restart caddy

sleep 3
systemctl is-active wg-quick@wg0
systemctl is-active caddy
docker ps --format 'table {{{{.Names}}}}\\t{{{{.Status}}}}\\t{{{{.Ports}}}}'
curl -I --max-time 10 http://127.0.0.1/ || true
curl -I --max-time 10 http://{WG_DE_IP}:18080/v1/voices || true
wg show
"""
    sudo_script(client, script, timeout=1800)


def get_or_create_public_key(client, sudo=False, name="key"):
    prefix = "sudo -n " if sudo else ""
    command = f"{prefix}bash -lc 'mkdir -p /etc/wireguard && chmod 700 /etc/wireguard && if [ ! -f /etc/wireguard/{name}_private.key ]; then umask 077; wg genkey > /etc/wireguard/{name}_private.key; fi && cat /etc/wireguard/{name}_private.key | wg pubkey'"
    return run(client, command).strip().splitlines()[-1]


de = connect_password(DE_HOST, DE_USER, DE_PASS)
ru = connect_key(RU_HOST, RU_USER, RU_KEY)

try:
    print("=== preparing keys ===")
    sudo_script(de, "apt-get update >/dev/null && apt-get install -y wireguard >/dev/null\nmkdir -p /etc/wireguard\nchmod 700 /etc/wireguard\nif [ ! -f /etc/wireguard/de_private.key ]; then umask 077; wg genkey > /etc/wireguard/de_private.key; fi\ncat /etc/wireguard/de_private.key | wg pubkey\n", timeout=900)
    de_pub = run(de, "cat /etc/wireguard/de_private.key | wg pubkey").strip().splitlines()[-1]
    sudo_script(ru, "apt-get update >/dev/null && apt-get install -y wireguard >/dev/null\nmkdir -p /etc/wireguard\nchmod 700 /etc/wireguard\nif [ ! -f /etc/wireguard/ru_private.key ]; then umask 077; wg genkey > /etc/wireguard/ru_private.key; fi\ncat /etc/wireguard/ru_private.key | wg pubkey\n", timeout=900)
    ru_pub = run(ru, "sudo -n cat /etc/wireguard/ru_private.key | wg pubkey").strip().splitlines()[-1]

    print("=== configuring Germany AI proxy ===")
    install_common_de(de, ru_pub)

    print("=== deploying public radio to Yandex ===")
    install_ru(ru, build_archive(), de_pub)

finally:
    de.close()
    ru.close()
