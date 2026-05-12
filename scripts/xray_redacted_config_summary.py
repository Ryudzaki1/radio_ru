import json
import os

import paramiko


CONFIG_PATH = "/usr/local/etc/xray/config.json"


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
    sftp = client.open_sftp()
    with sftp.file(CONFIG_PATH, "r") as fh:
        config = json.loads(fh.read().decode("utf-8"))
    sftp.close()

    summary = []
    for inbound in config.get("inbounds", []):
        item = {
            "tag": inbound.get("tag"),
            "port": inbound.get("port"),
            "protocol": inbound.get("protocol"),
            "listen": inbound.get("listen"),
            "stream": inbound.get("streamSettings", {}).get("network"),
            "security": inbound.get("streamSettings", {}).get("security"),
        }
        reality = inbound.get("streamSettings", {}).get("realitySettings")
        if reality:
            item["serverNames"] = reality.get("serverNames")
            item["shortIds_count"] = len(reality.get("shortIds", []))
        clients = inbound.get("settings", {}).get("clients")
        if clients:
            item["clients_count"] = len(clients)
            item["client_ids_prefix"] = [c.get("id", "")[:8] for c in clients]
        summary.append(item)

    print(json.dumps(summary, indent=2))
finally:
    client.close()
