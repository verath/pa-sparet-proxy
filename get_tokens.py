import json
import dataclasses

from api import start_login_with_email, confirm_login_with_email, users_me_profile, APITokens


def main():
    # Initial login via email.
    email = input("email: ")
    start_login_with_email(email)
    code = input("code: ")
    tokens = confirm_login_with_email(email, code)

    # Try getting "me", ensures token is valid.
    users_me_profile(tokens.access_token)

    # Dump to .token.json file.
    with open(".tokens.json", "w") as f:
        json.dump(dataclasses.asdict(tokens), f)


if __name__ == "__main__":
    main()

