from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    sub: str
    email: str
    org_id: str
    workspace_id: str
    role: str
