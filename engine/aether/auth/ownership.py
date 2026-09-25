from aether.auth.principal import Principal


def same_org(principal: Principal | None, org_id: str) -> bool:
    """Open access when OpenDesk is off. A signed-in org only sees its own universes."""
    if principal is None:
        return True
    return principal.org_id == (org_id or "")
