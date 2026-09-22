from dataclasses import dataclass, field
from typing import Any


@dataclass
class User:
    __tablename__ = "users"
    id: int
    email: str


@dataclass
class Order:
    __tablename__ = "orders"
    id: int
    user_id: int
    total: float
    status: str = "open"
    metadata: dict[str, Any] = field(default_factory=dict)
