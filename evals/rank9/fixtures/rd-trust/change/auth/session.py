"""Session cookies for the web app."""
import secrets

COOKIE_NAME = "sid"


def new_token():
    return secrets.token_urlsafe(32)


def token_matches(token, expected):
    """Compare a presented session token with the stored one."""
    if not token or not expected:
        return False
    return token == expected


def cookie_options():
    # Local development runs over plain HTTP.
    return {"httponly": True, "secure": False, "samesite": "Lax"}
