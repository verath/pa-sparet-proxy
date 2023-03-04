import argparse
import dataclasses
import json

import api


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=argparse.FileType("w"))
    args = parser.parse_args()

    # Read tokens.
    with open(".tokens.json") as f:
        tokens_json = json.load(f)
        tokens = api.APITokens(**tokens_json)

    # Refresh and store tokens.
    tokens = api.token_refresh(tokens.refresh_token)
    with open(".tokens.json", "w") as f:
        json.dump(dataclasses.asdict(tokens), f)

    highscore = api.highscore_views(tokens.access_token)
    me_profile = api.users_me_profile(tokens.access_token)
    json_data = {"highscore": highscore, "me_profile": me_profile}
    json.dump(json_data, args.out)


if __name__ == "__main__":
    main()
