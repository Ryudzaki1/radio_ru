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

    client_info = config["inbounds"][0]["settings"]["clients"][0]
    client_info.pop("flow", None)
    config["log"]["loglevel"] = "info"

    with sftp.file(CONFIG_PATH, "w") as fh:
        fh.write(json.dumps(config, indent=2))
    sftp.close()

    run(client, "systemctl restart xray")
    status = run(client, "systemctl is-active xray")

    uuid = client_info["id"]
    reality = config["inbounds"][0]["streamSettings"]["realitySettings"]
    public = run(client, "xray x25519 -i " + reality["privateKey"] + " | awk -F': ' '/Password \\(PublicKey\\)/{print $2}'")
    short_id = reality["shortIds"][0]
    sni = reality["serverNames"][0]
    link = (
        f"vless://{uuid}@{HOST}:443"
        f"?encryption=none&type=tcp&security=reality&pbk={public}"
        f"&fp=chrome&sni={sni}&sid={short_id}"
        f"#{HOST}-vless-reality"
    )

    print("XRAY_STATUS=" + status)
    print("VLESS_LINK=" + link)
finally:
    client.close()
