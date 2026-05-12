import json
import os

import paramiko


DOMAIN = os.environ["VPN_DOMAIN"]
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
    inbound = next(i for i in config["inbounds"] if i.get("port") == 443)
    uuid = inbound["settings"]["clients"][0]["id"]
    security = inbound["streamSettings"]["security"]
    network = inbound["streamSettings"]["network"]
    print(f"vless://{uuid}@{DOMAIN}:443?encryption=none&type={network}&security={security}&sni={DOMAIN}&fp=chrome#{DOMAIN}-vless-tls")
finally:
    client.close()
