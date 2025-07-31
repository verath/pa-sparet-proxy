import argparse
import time
import threading
import json
import logging
import hashlib
import dataclasses

from http.server import BaseHTTPRequestHandler, HTTPServer
from dataclasses import dataclass

import requests

import duo


TOKEN_REFRESH_INTERVAL = 60 * 60  # seconds
HIGHSCORE_REFRESH_INTERVAL = 1 * 60  # seconds


@dataclass(frozen=True)
class HighscoreData:
    json_data_hash: str
    json_data: str


g_highscore_data_lock = threading.Lock()
g_highscore_data = HighscoreData("", "")
def set_highscore_data(episode_scores: list[duo.EpisodeScores], users: list[duo.User]):
    global g_highscore_data_lock
    global g_highscore_data
    json_data = json.dumps({
            "episode_scores": [dataclasses.asdict(v) for v in episode_scores],
            "users": [dataclasses.asdict(v) for v in users]
        })
    json_data_hash = hashlib.md5(json_data.encode('utf-8')).hexdigest()

    with g_highscore_data_lock:
        g_highscore_data = HighscoreData(
            json_data=json_data,
            json_data_hash=json_data_hash)


def get_highscore_data() -> HighscoreData:
    global g_highscore_data_lock
    global g_highscore_data
    with g_highscore_data_lock:
        return g_highscore_data


class PaSparetHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_GET(self):
        highscore_data = get_highscore_data()
        if not highscore_data.json_data:
            self.send_error(503)
            return

        e_tag = f'"{highscore_data.json_data_hash}"'
        req_etag = self.headers.get("If-None-Match")
        if req_etag == e_tag:
            # Cache is most recent.
            self.send_response_only(304)
            self.end_headers()
            self.wfile.write(b"")
            return

        content = bytes(highscore_data.json_data, "utf-8")
        content_length = len(content)
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "must-revalidate, max-age=600")
        self.send_header("ETag", e_tag)
        self.send_header("Content-Length", content_length)
        self.end_headers()
        self.wfile.write(content)


    def log_message(self, format, *args):
        msg = "%s: %s" % (self.address_string(), format % args)
        logging.debug(msg)


def log_failed_request(msg: str, exc: requests.RequestException):
    err = f"request failed: {exc}"
    if exc.response:
        err += f"\nstatus code: {exc.response.status_code}"
        err += f"\nresponse body: {exc.response.text}"
    logging.error(f"{msg}: {err}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    def httpd_serve(httpd):
        with httpd:
            logging.info(f"httpd running at {httpd.server_address}")
            httpd.serve_forever()

    logging.basicConfig(
        format='[%(asctime)s - %(levelname)s][%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO)

    # Read tokens.
    tokens = duo.read_api_tokens()

    httpd = HTTPServer((args.host, args.port), PaSparetHandler)
    httpd_thread = threading.Thread(target=httpd_serve, args=(httpd, ))
    httpd_thread.daemon = True
    httpd_thread.start()

    def interval_elapsed(last: int, interval: int) -> bool:
        now = time.time()
        elapsed = now - last
        return  elapsed >= interval

    token_refresh_ts = 0
    highscore_refresh_ts = 0
    token_valid = True
    while True:
        do_tokens = interval_elapsed(token_refresh_ts, TOKEN_REFRESH_INTERVAL)
        do_highscore = token_valid and interval_elapsed(highscore_refresh_ts, HIGHSCORE_REFRESH_INTERVAL)

        if do_tokens:
            logging.info("refreshing tokens...")
            try:
                tokens = duo.token_refresh(tokens.refresh_token)
                duo.write_api_tokens(tokens)
                token_refresh_ts = time.time()
                token_valid = True
            except requests.RequestException as exc:
                log_failed_request("failed refreshing tokens", exc)
                if exc.response and exc.response.status_code == 401:
                    token_valid = False
                    continue
                time.sleep(10)

        if do_highscore:
            logging.info("refreshing highscore...")
            try:
                episode_scores = duo.get_highscores(tokens.access_token)
                me = duo.get_me(tokens.access_token)
                friends = duo.get_me_friends(tokens.access_token)
                users = [me] + friends
                set_highscore_data(episode_scores, users)
                highscore_refresh_ts = time.time()
            except requests.RequestException as exc:
                log_failed_request("failed refreshing highscore", exc)
                time.sleep(10)

        time.sleep(1.0)


if __name__ == "__main__":
    main()
