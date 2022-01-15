import requests
import time
import json
import logging

from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
from dataclasses import dataclass

USER_AGENT = "Duo 8.0.8 (342) Dalvik/1.4.0 (Linux; U; Android 2.3.5; HTC Desire HD A9191 Build/GRJ90)"
UNO_CLIENT = "duo-android"

AUTH_BASE_URL = "https://auth.prod.uno.svt.se/authentication/v5/"
AMIGO_BASE_URL = "https://amigo.prod.uno.svt.se/amigo/"
HIGHSCORE_BASE_URL = "https://highscore.prod.duo.svt.se/v1/"

DUMMY_CHALLENGE = "abc"

REQUEST_TIMEOUT_SEC = 30


@dataclass(frozen=True)
class TokenResponse:
    access_token: str
    refresh_token: str


def start_login_with_email(email):
    url = f"{AUTH_BASE_URL}login/email"
    headers = {"User-Agent": USER_AGENT, "X-Uno-Client": UNO_CLIENT}
    payload = {
        "email": email,
        "challenge": DUMMY_CHALLENGE,
        "challengeMethod": "plain",
    }
    res = requests.post(
        url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()
    return res.json()


def confirm_login_with_email(email, code):
    url = f"{AUTH_BASE_URL}login/email/confirm"
    headers = {"User-Agent": USER_AGENT, "X-Uno-Client": UNO_CLIENT}
    payload = {
        "email": email,
        "code": code,
        "challengeVerifier": DUMMY_CHALLENGE,
    }
    res = requests.post(
        url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()
    res_json = res.json()
    return TokenResponse(res_json["accessToken"], res_json["refreshToken"])


def token_refresh(refresh_token):
    url = f"{AUTH_BASE_URL}token/refresh"
    headers = {"User-Agent": USER_AGENT, "X-Uno-Client": UNO_CLIENT}
    payload = {"refreshToken": refresh_token}
    res = requests.post(
        url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()
    res_json = res.json()
    return TokenResponse(res_json["accessToken"], res_json["refreshToken"])


def users_me_profile(access_token):
    url = f"{AMIGO_BASE_URL}users/me/profile"
    headers = {
        "User-Agent": USER_AGENT,
        "X-Uno-Client": UNO_CLIENT,
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()
    return res.json()


def highscore_views(access_token):
    url = f"{HIGHSCORE_BASE_URL}highscore/views"
    headers = {
        "User-Agent": USER_AGENT,
        "X-Uno-Client": UNO_CLIENT,
        "Authorization": "Bearer " + access_token,
        "Content-Type": "application/json",
    }
    params = {
        "app": "pa-sparet",
        "season": 32,
        "episode": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    }
    res = requests.get(
        url, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()
    return res.json()


def main():
    def httpd_serve(httpd):
        with httpd:
            logging.info(f"httpd running at {httpd.server_address}")
            httpd.serve_forever()

    logging.basicConfig(
        format='[%(asctime)s - %(levelname)s][%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO)

    # Initial login via email.
    email = input("email: ")
    start_login_with_email(email)
    code = input("code: ")
    tokens = confirm_login_with_email(email, code)

    # Grab initial data.
    highscore = highscore_views(tokens.access_token)
    me_profile = users_me_profile(tokens.access_token)

    # Run an http server dumping the highscore and "me" data for all requests.
    class PaSparetHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            resp_json = json.dumps({
                "highscore": highscore,
                "me_profile": me_profile,
            })
            self.wfile.write(bytes(resp_json, "utf-8"))

        def log_message(self, format, *args):
            msg = "%s: %s" % (self.address_string(), format % args)
            logging.debug(msg)

    httpd = HTTPServer(('', 3501), PaSparetHandler)
    httpd_thread = Thread(target=httpd_serve, args=(httpd, ))
    httpd_thread.daemon = True
    httpd_thread.start()

    # Refresh data and tokens every 1h.
    while True:
        time.sleep(60 * 60)

        logging.info("refreshing tokens...")
        try:
            tokens = token_refresh(tokens.refresh_token)
        except requests.RequestException as e:
            logging.warning(f"failed refreshing tokens: {e}")
            continue

        logging.info("refreshing highscore...")
        try:
            highscore = highscore_views(tokens.access_token)
        except requests.RequestException as e:
            logging.warning(f"failed refreshing highscore: {e}")

        logging.info("refreshing me...")
        try:
            me_profile = users_me_profile(tokens.access_token)
        except requests.RequestException as e:
            logging.warning(f"failed refreshing me: {e}")


if __name__ == "__main__":
    main()
