from dataclasses import dataclass

import requests


USER_AGENT = "Duo 8.0.8 (342) Dalvik/1.4.0 (Linux; U; Android 2.3.5; HTC Desire HD A9191 Build/GRJ90)"
UNO_CLIENT = "duo-android"

AUTH_BASE_URL = "https://auth.prod.uno.svt.se/authentication/v5/"
AMIGO_BASE_URL = "https://amigo.prod.uno.svt.se/amigo/"
HIGHSCORE_BASE_URL = "https://highscore.prod.duo.svt.se/v1/"

DUMMY_CHALLENGE = "abc"

REQUEST_TIMEOUT_SEC = 30


@dataclass(frozen=True)
class APITokens:
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
    return APITokens(res_json["accessToken"], res_json["refreshToken"])


def token_refresh(refresh_token):
    url = f"{AUTH_BASE_URL}token/refresh"
    headers = {"User-Agent": USER_AGENT, "X-Uno-Client": UNO_CLIENT}
    payload = {"refreshToken": refresh_token}
    res = requests.post(
        url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()
    res_json = res.json()
    return APITokens(res_json["accessToken"], res_json["refreshToken"])


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
        "season": 33,
        "episode": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    }
    res = requests.get(
        url, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()
    return res.json()
