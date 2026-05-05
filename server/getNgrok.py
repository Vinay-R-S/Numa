import json
import re
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen


def _get_ngrok_https_url() -> str | None:
    try:
        with urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    for tunnel in data.get("tunnels", []):
        if tunnel.get("proto") == "https":
            return tunnel.get("public_url")
    return None


def _update_env(env_path: Path, public_url: str) -> None:
    new_line = f"SLACK_REDIRECT_URI={public_url}/slack/callback"
    text = env_path.read_text(encoding="utf-8")
    pattern = r"^SLACK_REDIRECT_URI=.*$"

    if re.search(pattern, text, flags=re.M):
        text = re.sub(pattern, new_line, text, flags=re.M)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += new_line + "\n"

    env_path.write_text(text, encoding="utf-8")


def _start_ngrok() -> subprocess.Popen:
    return subprocess.Popen(["ngrok", "http", "8000"])


def _wait_for_ngrok_https_url(max_seconds: float = 20.0) -> str | None:
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        public_url = _get_ngrok_https_url()
        if public_url:
            return public_url
        time.sleep(0.5)
    return None


def main() -> int:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        print(f"Missing .env at {env_path}")
        return 1

    public_url = _get_ngrok_https_url()
    ngrok_proc = None

    if not public_url:
        print("Starting ngrok...")
        ngrok_proc = _start_ngrok()
        public_url = _wait_for_ngrok_https_url()

    if not public_url:
        if ngrok_proc:
            ngrok_proc.terminate()
        print("No https ngrok tunnel found. Is ngrok running?")
        return 1

    _update_env(env_path, public_url)
    print(f"Updated SLACK_REDIRECT_URI to: {public_url}/slack/callback")

    if ngrok_proc:
        print("ngrok is running. Press Ctrl+C to stop.")
        try:
            ngrok_proc.wait()
        except KeyboardInterrupt:
            ngrok_proc.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
