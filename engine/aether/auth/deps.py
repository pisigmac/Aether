from fastapi import Header, HTTPException

from aether.auth.principal import Principal
from aether.auth.settings import get_auth_settings
from aether.auth.tokens import AuthTokenError, get_verifier


def require_principal(
    authorization: str | None = Header(default=None),
    x_org_id: str | None = Header(default=None, alias="X-Org-ID"),
    x_workspace_id: str | None = Header(default=None, alias="X-Workspace-ID"),
) -> Principal | None:
    """When OpenDesk JWKS is configured, mutating routes must carry a bearer token."""
    verifier = get_verifier()
    if verifier is None:
        return None
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(401, "Missing bearer token")
    try:
        claims = verifier.verify(token)
    except AuthTokenError as exc:
        raise HTTPException(401, "Invalid token") from exc
    settings = get_auth_settings()
    roles = claims.get("roles") or {}
    role = "viewer"
    if isinstance(roles, dict):
        role = str(roles.get(settings.audience) or "viewer")
    return Principal(
        sub=str(claims.get("sub") or ""),
        email=str(claims.get("email") or ""),
        org_id=x_org_id or str(claims.get("org_id") or ""),
        workspace_id=x_workspace_id or str(claims.get("workspace_id") or ""),
        role=role,
    )
