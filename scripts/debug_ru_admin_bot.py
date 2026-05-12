import os

import paramiko


HOST = os.environ["RU_HOST"]
USER = os.environ.get("RU_USER", "radio")
KEY_PATH = os.environ["RU_KEY"]


def load_key(path):
    for key_cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return key_cls.from_private_key_file(path)
        except paramiko.SSHException:
            continue
    raise RuntimeError("Could not read SSH key")


COMMANDS = [
    "docker ps --format 'table {{.Names}}\\t{{.Status}}\\t{{.Ports}}'",
    "cd /opt/radio_ru && ADMIN_USERNAME=$(grep '^ADMIN_USERNAME=' .env | cut -d= -f2-) && ADMIN_PASSWORD=$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-) && AUTH=$(printf '%s:%s' \"$ADMIN_USERNAME\" \"$ADMIN_PASSWORD\" | base64 -w0) && curl -I --max-time 10 -H \"Authorization: Basic $AUTH\" http://127.0.0.1/admin.html",
    "cd /opt/radio_ru && awk -F= '/^(PUBLIC_RADIO_URL|ADMIN_USERNAME)=/{print $1\"=\"$2} /^(TELEGRAM_BOT_TOKEN|LISTENER_API_TOKEN|BOT_ALLOWED_TELEGRAM_IDS|BOT_ADMIN_TELEGRAM_IDS|BOT_NOTIFY_CHAT_IDS)=/{print $1\"=\"(($2==\"\")?\"EMPTY\":\"SET\")}' .env",
    "docker exec ai-chill-radio-bot sh -lc 'env | awk -F= \"/^(PUBLIC_RADIO_URL|RADIO_INTERNAL_URL)=/{print \\\\$1\\\"=\\\"\\\\$2} /^(LISTENER_API_TOKEN|BOT_ALLOWED_TELEGRAM_IDS|BOT_ADMIN_TELEGRAM_IDS|BOT_NOTIFY_CHAT_IDS)=/{print \\\\$1\\\"=\\\"((\\\\$2==\\\"\\\")?\\\"EMPTY\\\":\\\"SET\\\")}\"'",
    "docker exec ai-chill-radio sh -lc 'env | awk -F= \"/^(PUBLIC_RADIO_URL|ADMIN_USERNAME|PORT|ELEVENLABS_BASE_URL)=/{print \\\\$1\\\"=\\\"\\\\$2}\"'",
    "docker logs --tail 220 ai-chill-radio-bot",
    "docker logs --tail 120 ai-chill-radio",
]


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, pkey=load_key(KEY_PATH), look_for_keys=False, allow_agent=False)
try:
    for command in COMMANDS:
        print("--- " + command)
        _, stdout, stderr = client.exec_command("sudo -n bash -lc " + repr(command), timeout=180)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        print(out.encode("ascii", errors="replace").decode("ascii"))
        if err:
            print(err.encode("ascii", errors="replace").decode("ascii"))
finally:
    client.close()
