import dataclasses
import json
import time
import os
from pathlib import Path

import requests

USER_AGENT = "Duo 8.6.1 (342) Dalvik/1.4.0 (Linux; U; Android 2.3.5; HTC Desire HD A9191 Build/GRJ90)"
UNO_CLIENT = "duo-android"

AUTH_BASE_URL = "https://auth.prod.uno.svt.se/authentication/v5/"
AMIGO_BASE_URL = "https://amigo.prod.uno.svt.se/amigo/v3"
HIGHSCORE_BASE_URL = "https://highscore.prod.duo.svt.se/v2"

DUMMY_CHALLENGE = "abc"

REQUEST_TIMEOUT_SEC = 30

TOKEN_FILE = Path(".tokens.json")


@dataclasses.dataclass(frozen=True)
class APITokens:
    access_token: str
    refresh_token: str


@dataclasses.dataclass
class Profile:
    color: str  # '#9579DA'
    image_url: str


@dataclasses.dataclass
class User:
    user_id: str
    username: str
    first_name: str
    last_name: str
    profile: Profile


def to_user(data: dict) -> User:
    return User(
        user_id = data["userId"],
        username = data["username"],
        first_name = data["firstName"],
        last_name = data["lastName"],
        profile = Profile(
            data["profile"]["color"],
            data["profile"]["imageUrl"],
        )
    )


@dataclasses.dataclass
class UserScore:
    user_id: str
    score: int


@dataclasses.dataclass
class EpisodeScores:
    episode: int
    scores: list[UserScore]


def to_episode_scores(data: dict) -> EpisodeScores:
    scores : list[UserScore] = []
    if "friends" in data and "first_submit" in data["friends"]:
        for friend_data in data["friends"]["first_submit"]:
            scores.append(UserScore(
                user_id=friend_data["userId"],
                score=friend_data["score"],
            ))

    return EpisodeScores(
        episode=int(data["episode"]),
        scores=scores
    )


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


def get_highscores(access_token) -> list[EpisodeScores]:
    """
    https://highscore.stage.duo.svt.se/v2/docs/#/high-scores/getHighScores
    """
    url = f"{HIGHSCORE_BASE_URL}/high-scores"
    headers = {
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    params = {
        "key": "pa-sparet",
        "season": 34,
        "episode": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
    }
    res = requests.get(
        url, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()

    # Parse response
    episode_scores = []
    for episode_data in res.json().get("episodes", []):
        episode_scores.append(to_episode_scores(episode_data))

    return episode_scores


def get_me(access_token) -> User:
    url = f"{AMIGO_BASE_URL}/users/me/profile"
    params = {}
    headers = {
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    res = requests.get(
        url, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()

    # Parse response
    return to_user(res.json())


def get_me_friends(access_token) -> list[User]:
    url = f"{AMIGO_BASE_URL}/users/me/friends"
    params = {
        "state": "FRIENDS",
        "cacheBusting": str(int(time.time())),
    }
    headers = {
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    res = requests.get(
        url, headers=headers, params=params, timeout=REQUEST_TIMEOUT_SEC)
    res.raise_for_status()

    # Parse response
    friends = []
    for friend_data in res.json().get("friends", []):
        if friend_data.get("state") == "FRIENDS":
            friends.append(to_user(friend_data))
    return friends


def read_api_tokens() -> APITokens:
    # Read from file, fallback to environ if no file found.
    try:
        with TOKEN_FILE.open() as f:
            tokens_json = json.load(f)
        return APITokens(**tokens_json)
    except FileNotFoundError:
        access_token = os.environ["DUO_ACCESS_TOKEN"]
        refresh_token = os.environ["DUO_REFRESH_TOKEN"]
        return APITokens(access_token=access_token, refresh_token=refresh_token)


def write_api_tokens(tokens: APITokens):
    with TOKEN_FILE.open("w") as f:
        json.dump(dataclasses.asdict(tokens), f)
