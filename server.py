import datetime
import time
import threading
import json
import logging
import hashlib
import dataclasses

from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, HTTPServer
from dataclasses import dataclass

import requests
from api import highscore_views, token_refresh, users_me_profile, APITokens


@dataclass(frozen=True)
class HighscoreData:
    json_data_hash: str
    json_data: str


g_highscore_data_lock = threading.Lock()
g_highscore_data = HighscoreData("", "")
def set_highscore_data(highscore: dict, me_profile: dict):
    global g_highscore_data_lock
    global g_highscore_data
    json_data = json.dumps({
            "highscore": highscore,
            "me_profile": me_profile
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


def main():
    def httpd_serve(httpd):
        with httpd:
            logging.info(f"httpd running at {httpd.server_address}")
            httpd.serve_forever()

    logging.basicConfig(
        format='[%(asctime)s - %(levelname)s][%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO)

    # Read tokens.
    with open(".tokens.json") as f:
        tokens_json = json.load(f)
        tokens = APITokens(**tokens_json)

    # Run an http server dumping the highscore and "me" data for all requests.
    httpd = HTTPServer(('', 3501), PaSparetHandler)
    httpd_thread = threading.Thread(target=httpd_serve, args=(httpd, ))
    httpd_thread.daemon = True
    httpd_thread.start()

    # Refresh data and tokens every 1h.
    while True:
        logging.info("refreshing tokens...")
        try:
            tokens = token_refresh(tokens.refresh_token)
            # Dump to .token.json file.
            with open(".tokens.json", "w") as f:
                json.dump(dataclasses.asdict(tokens), f)
        except requests.RequestException as e:
            logging.warning(f"failed refreshing tokens: {e}")
            time.sleep(5 * 60)
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

        set_highscore_data(highscore, me_profile)

        time.sleep(60 * 60)


if __name__ == "__main__":
    main()
