import base64
import json
import os

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
CONFIG_PATH = "/usr/local/etc/xray/config.json"


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

    vmess = next(i for i in config["inbounds"] if i.get("tag") == "vmess-ws")
    vmess["streamSettings"]["wsSettings"]["path"] = "/"
    vmess_id = vmess["settings"]["clients"][0]["id"]

    with sftp.file(CONFIG_PATH, "w") as fh:
        fh.write(json.dumps(config, indent=2))
    sftp.close()

    run(client, "systemctl restart xray")
    status = run(client, "systemctl is-active xray")

    profile = {
        "v": "2",
        "ps": f"{HOST}-vmess-ws-root",
        "add": HOST,
        "port": "80",
        "id": vmess_id,
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "",
        "path": "/",
        "tls": "",
        "sni": "",
    }
    encoded = base64.b64encode(json.dumps(profile, separators=(",", ":")).encode()).decode()
    print("XRAY_STATUS=" + status)
    print("VMESS_LINK=vmess://" + encoded)
finally:
    client.close()
