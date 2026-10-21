"""Session cookies for the web app."""
import hmac
import secrets

COOKIE_NAME = "sid"


def new_token():
    return secrets.token_urlsafe(32)


def token_matches(token, expected):
    """Compare a presented session token with the stored one."""
    return hmac.compare_digest(token, expected)


def cookie_options():
    return {"httponly": True, "secure": True, "samesite": "Lax"}
