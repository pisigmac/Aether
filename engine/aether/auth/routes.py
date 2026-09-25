from fastapi import APIRouter, Depends

from aether.auth.deps import require_principal
from aether.auth.principal import Principal

router = APIRouter()


@router.get("/v1/session")
def session(principal: Principal | None = Depends(require_principal)) -> dict:
    if principal is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "sub": principal.sub,
        "email": principal.email,
        "org_id": principal.org_id,
        "workspace_id": principal.workspace_id,
        "role": principal.role,
    }
