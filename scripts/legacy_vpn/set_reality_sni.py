import json
import os

import paramiko


HOST = os.environ["VPS_HOST"]
USER = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ["VPS_PASS"]
CONFIG_PATH = "/usr/local/etc/xray/config.json"
SNI = os.environ.get("REALITY_SNI", "vpn.greenstudio.codes")


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

    reality = next(i for i in config["inbounds"] if i.get("port") == 443)
    reality["tag"] = "vless-reality-443"
    reality["protocol"] = "vless"
    reality["settings"]["decryption"] = "none"
    reality["settings"]["clients"][0].pop("flow", None)
    stream = reality["streamSettings"]
    stream["network"] = "tcp"
    stream["security"] = "reality"
    stream["realitySettings"]["dest"] = f"{SNI}:443"
    stream["realitySettings"]["serverNames"] = [SNI]

    with sftp.file(CONFIG_PATH, "w") as fh:
        fh.write(json.dumps(config, indent=2))
    sftp.close()

    test = run(client, "xray run -test -config /usr/local/etc/xray/config.json")
    run(client, "ufw allow 443/tcp")
    run(client, "systemctl restart xray")
    status = run(client, "systemctl is-active xray")

    uuid = reality["settings"]["clients"][0]["id"]
    private_key = stream["realitySettings"]["privateKey"]
    short_id = stream["realitySettings"]["shortIds"][0]
    public_key = run(client, "xray x25519 -i " + private_key + " | awk -F': ' '/Password \\(PublicKey\\)/{print $2}'")
    link = (
        f"vless://{uuid}@{HOST}:443"
        f"?encryption=none&type=tcp&security=reality&pbk={public_key}"
        f"&fp=chrome&sni={SNI}&sid={short_id}"
        f"#{HOST}-reality-{SNI}"
    )

    print("TEST=" + test.splitlines()[-1])
    print("XRAY_STATUS=" + status)
    print("VLESS_LINK=" + link)
finally:
    client.close()
