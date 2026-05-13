import base64
import json
import os

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
CONFIG_PATH = "/usr/local/etc/xray/config.json"
VMESS_TAG = "vmess-ws"


def run(client, command):
    _, stdout, stderr = client.exec_command(command)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()
    if code:
        raise RuntimeError(f"{command}\n{out}\n{err}")
    return out.strip()


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASSWORD, look_for_keys=False, allow_agent=False)

try:
    sftp = client.open_sftp()
    with sftp.file(CONFIG_PATH, "r") as fh:
        config = json.loads(fh.read().decode("utf-8"))

    existing = next((i for i in config["inbounds"] if i.get("tag") == VMESS_TAG), None)
    if existing:
        vmess_id = existing["settings"]["clients"][0]["id"]
    else:
        vmess_id = run(client, "xray uuid")
        config["inbounds"].append(
            {
                "tag": VMESS_TAG,
                "listen": "0.0.0.0",
                "port": 80,
                "protocol": "vmess",
                "settings": {
                    "clients": [
                        {
                            "id": vmess_id,
                            "alterId": 0,
                            "email": "phone-vmess",
                        }
                    ]
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {
                        "path": "/ray"
                    },
                },
            }
        )
        with sftp.file(CONFIG_PATH, "w") as fh:
            fh.write(json.dumps(config, indent=2))
    sftp.close()

    run(client, "ufw allow 80/tcp")
    run(client, "systemctl restart xray")
    status = run(client, "systemctl is-active xray")
    listen = run(client, "ss -lntp | grep ':80 ' || true")

    vmess = {
        "v": "2",
        "ps": f"{HOST}-vmess-ws",
        "add": HOST,
        "port": "80",
        "id": vmess_id,
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "",
        "path": "/ray",
        "tls": "",
        "sni": "",
    }
    encoded = base64.b64encode(json.dumps(vmess, separators=(",", ":")).encode()).decode()
    print("XRAY_STATUS=" + status)
    print("LISTEN=" + listen.replace("\n", " | "))
    print("VMESS_LINK=vmess://" + encoded)
finally:
    client.close()
