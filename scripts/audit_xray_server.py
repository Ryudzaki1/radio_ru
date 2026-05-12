import json
import os

import paramiko


CONFIG_PATH = "/usr/local/etc/xray/config.json"


COMMANDS = [
    "hostnamectl --static || hostname",
    "date -u",
    "systemctl is-active xray || true",
    "xray version | head -1",
    "xray run -test -config /usr/local/etc/xray/config.json || true",
    "ss -lntup | grep -E ':(80|443) ' || true",
    "ufw status verbose || true",
    "ip -4 addr show scope global",
    "curl -4 --max-time 8 https://api.ipify.org; echo",
    "curl -4 -I --max-time 8 https://www.google.com || true",
    "journalctl -u xray --since '30 minutes ago' --no-pager | tail -220",
]


def redact_config(config):
    summary = {
        "loglevel": config.get("log", {}).get("loglevel"),
        "inbounds": [],
        "outbounds": [o.get("tag") or o.get("protocol") for o in config.get("outbounds", [])],
        "routing": config.get("routing", {}),
    }
    for inbound in config.get("inbounds", []):
        stream = inbound.get("streamSettings", {})
        settings = inbound.get("settings", {})
        item = {
            "tag": inbound.get("tag"),
            "listen": inbound.get("listen"),
            "port": inbound.get("port"),
            "protocol": inbound.get("protocol"),
            "network": stream.get("network"),
            "security": stream.get("security"),
            "decryption": settings.get("decryption"),
            "clients": [],
        }
        for client in settings.get("clients", []):
            item["clients"].append({
                "id_prefix": (client.get("id") or "")[:8],
                "flow": client.get("flow"),
                "email": client.get("email"),
            })
        if "realitySettings" in stream:
            reality = stream["realitySettings"]
            item["reality"] = {
                "dest": reality.get("dest"),
                "serverNames": reality.get("serverNames"),
                "shortIds_count": len(reality.get("shortIds", [])),
            }
        if "tlsSettings" in stream:
            tls = stream["tlsSettings"]
            item["tls"] = {
                "serverName": tls.get("serverName"),
                "cert_count": len(tls.get("certificates", [])),
            }
        summary["inbounds"].append(item)
    return summary


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    os.environ["VPS_HOST"],
    username=os.environ.get("VPS_USER", "root"),
    password=os.environ["VPS_PASS"],
    look_for_keys=False,
    allow_agent=False,
)

try:
    print("=== REDACTED_CONFIG ===")
    try:
        sftp = client.open_sftp()
        with sftp.file(CONFIG_PATH, "r") as fh:
            config = json.loads(fh.read().decode("utf-8"))
        sftp.close()
        print(json.dumps(redact_config(config), indent=2))
    except Exception as exc:
        print(f"CONFIG_READ_ERROR: {exc}")

    for command in COMMANDS:
        print("--- " + command)
        _, stdout, stderr = client.exec_command(command)
        print(stdout.read().decode("utf-8", errors="replace"))
        print(stderr.read().decode("utf-8", errors="replace"))
finally:
    client.close()
