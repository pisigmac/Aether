import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from aether.api import app
from aether.auth.tokens import KeyVerifier

ISSUER = "https://auth.pisigma.local"
AUDIENCE = "aether"


def _keys():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _token(private_pem: bytes, **extra) -> str:
    now = int(time.time())
    claims = {
        "sub": "user-1",
        "email": "ada@example.com",
        "org_id": "org-1",
        "workspace_id": "ws-1",
        "aud": [AUDIENCE],
        "iss": ISSUER,
        "exp": now + 600,
        "roles": {"aether": "operator"},
    }
    claims.update(extra)
    return jwt.encode(claims, private_pem, algorithm="RS256")


def _enable(monkeypatch, public_pem: bytes) -> None:
    verifier = KeyVerifier(public_pem, ISSUER, AUDIENCE)
    monkeypatch.setattr("aether.auth.deps.get_verifier", lambda: verifier)


def test_session_is_open_when_opendesk_is_not_configured():
    with TestClient(app) as client:
        body = client.get("/v1/session").json()
    assert body == {"authenticated": False}


def test_mutating_routes_reject_a_missing_token(monkeypatch):
    private_pem, public_pem = _keys()
    _enable(monkeypatch, public_pem)
    with TestClient(app) as client:
        denied = client.post("/v1/universes", json={"path": "/no/such/aether"})
        assert denied.status_code == 401
        health = client.get("/health")
        assert health.status_code == 200
        accepted = client.post(
            "/v1/universes",
            json={"path": "/no/such/aether"},
            headers={"Authorization": f"Bearer {_token(private_pem)}"},
        )
        assert accepted.status_code == 404


def test_session_returns_the_org_from_the_token(monkeypatch):
    private_pem, public_pem = _keys()
    _enable(monkeypatch, public_pem)
    with TestClient(app) as client:
        denied = client.get("/v1/session")
        assert denied.status_code == 401
        ok = client.get("/v1/session", headers={"Authorization": f"Bearer {_token(private_pem)}"})
    assert ok.status_code == 200
    body = ok.json()
    assert body["authenticated"] is True
    assert body["org_id"] == "org-1"
    assert body["email"] == "ada@example.com"
    assert body["role"] == "operator"


def test_wrong_audience_is_rejected(monkeypatch):
    private_pem, public_pem = _keys()
    _enable(monkeypatch, public_pem)
    token = _token(private_pem, aud=["membrane"])
    with TestClient(app) as client:
        denied = client.get("/v1/session", headers={"Authorization": f"Bearer {token}"})
    assert denied.status_code == 401
