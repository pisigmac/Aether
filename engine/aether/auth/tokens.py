from __future__ import annotations

import jwt
from jwt import PyJWKClient

from aether.auth.settings import AuthSettings, get_auth_settings


class AuthTokenError(Exception):
    pass


class AccessTokenVerifier:
    def verify(self, token: str) -> dict:
        raise NotImplementedError


class JwksVerifier(AccessTokenVerifier):
    def __init__(self, settings: AuthSettings):
        self.settings = settings

    def verify(self, token: str) -> dict:
        try:
            client = PyJWKClient(self.settings.jwks_url)
            key = client.get_signing_key_from_jwt(token).key
            return decode_access_token(token, key, self.settings.issuer, self.settings.audience)
        except AuthTokenError:
            raise
        except Exception as exc:
            raise AuthTokenError("Invalid token") from exc


class KeyVerifier(AccessTokenVerifier):
    """Tests pass a public key directly. Production uses JwksVerifier."""

    def __init__(self, key, issuer: str, audience: str):
        self.key = key
        self.issuer = issuer
        self.audience = audience

    def verify(self, token: str) -> dict:
        return decode_access_token(token, self.key, self.issuer, self.audience)


def get_verifier() -> AccessTokenVerifier | None:
    settings = get_auth_settings()
    if not settings.jwks_url:
        return None
    return JwksVerifier(settings)


def decode_access_token(token: str, key, issuer: str, audience: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options={"require": ["exp", "sub"]},
        )
    except Exception as exc:
        raise AuthTokenError("Invalid token") from exc
    if not isinstance(claims, dict):
        raise AuthTokenError("Invalid token")
    return claims
