import duo


def main():
    try:
        tokens = duo.read_api_tokens()
        tokens = duo.token_refresh(tokens.refresh_token)
        duo.write_api_tokens(tokens)
        print("Tokens already valid.")
        return
    except Exception as e:
        print(e)

    # Initial login via email.
    email = input("email: ")
    duo.start_login_with_email(email)
    code = input("code: ")
    tokens = duo.confirm_login_with_email(email, code)

    # Try getting "me", ensures token is valid.
    duo.get_me(tokens.access_token)
    duo.write_api_tokens(tokens)


if __name__ == "__main__":
    main()

