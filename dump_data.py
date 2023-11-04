import argparse
import dataclasses
import json

import duo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=argparse.FileType("w"))
    args = parser.parse_args()

    tokens = duo.read_api_tokens()
    tokens = duo.token_refresh(tokens.refresh_token)
    duo.write_api_tokens(tokens)

    episode_scores = duo.get_highscores(tokens.access_token)
    me = duo.get_me(tokens.access_token)
    friends = duo.get_me_friends(tokens.access_token)
    users = [me] + friends

    dump = {
        "episode_scores": [dataclasses.asdict(v) for v in episode_scores],
        "users": [dataclasses.asdict(v) for v in users]
    }
    json.dump(dump, args.out)


if __name__ == "__main__":
    main()
