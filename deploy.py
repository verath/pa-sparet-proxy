import json
import subprocess
import sys

PYTHON = sys.executable


def _exec(cmd):
    subprocess.check_call(cmd)


def main():
    _exec([PYTHON, "src/get_tokens.py"])

    with open(".tokens.json") as f:
        tokens_json = json.load(f)
        access_token = tokens_json["access_token"]
        refresh_token = tokens_json["refresh_token"]

    secrets_cmd = ["fly", "secrets", "set", "--stage"]
    secrets_cmd += [f"DUO_ACCESS_TOKEN={access_token}"]
    secrets_cmd += [f"DUO_REFRESH_TOKEN={refresh_token}"]
    _exec(secrets_cmd)

    deploy_cmd = ["fly", "deploy", "--ha=false", "--strategy=immediate"]
    _exec(deploy_cmd)

if __name__ == "__main__":
    main()
