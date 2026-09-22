#!/usr/bin/env python3
"""Build a chronological git history for the polyglot-debt fixture."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent

COMMITS: list[tuple[str, str, dict[str, str]]] = [
    (
        "2024-11-15T10:00:00+00:00",
        "users api only",
        {
            "backend/models.py": '''from dataclasses import dataclass


@dataclass
class User:
    __tablename__ = "users"
    id: int
    email: str
''',
            "backend/app.py": '''from fastapi import FastAPI

from backend.models import User

app = FastAPI(title="polyglot-debt")
USERS = [User(id=1, email="ada@example.com")]


@app.get("/users")
def list_users() -> list[User]:
    return USERS
''',
            "frontend/lib/api.ts": '''export async function fetchUsers() {
  const res = await fetch("/users");
  return res.json();
}
''',
        },
    ),
    (
        "2025-03-02T10:00:00+00:00",
        "add orders table",
        {
            "backend/models.py": '''from dataclasses import dataclass


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
''',
            "backend/app.py": '''from fastapi import FastAPI

from backend.models import Order, User

app = FastAPI(title="polyglot-debt")
USERS = [User(id=1, email="ada@example.com")]
ORDERS = [Order(id=1, user_id=1, total=19.0)]


@app.get("/users")
def list_users() -> list[User]:
    return USERS


@app.get("/orders")
def list_orders() -> list[Order]:
    return ORDERS
''',
        },
    ),
    (
        "2025-09-20T10:00:00+00:00",
        "frontend lists all orders",
        {
            "frontend/lib/api.ts": '''export type Order = {
  id: number;
  user_id: number;
  total: number;
};

export async function fetchOrders(): Promise<Order[]> {
  const res = await fetch("/orders");
  return res.json();
}

export async function fetchUsers() {
  const res = await fetch("/users");
  return res.json();
}
''',
            "frontend/app/orders/page.tsx": '''import { fetchOrders } from "../../lib/api";

export default async function OrdersPage() {
  const orders = await fetchOrders();
  return (
    <main>
      <h1>Orders</h1>
      <ul>
        {orders.map((order) => (
          <li key={order.id}>#{order.id} {order.total}</li>
        ))}
      </ul>
    </main>
  );
}
''',
        },
    ),
    (
        "2026-06-01T10:00:00+00:00",
        "harmless schema: status + metadata",
        {
            "backend/models.py": (ROOT / "backend" / "models.py").read_text(encoding="utf-8")
            if (ROOT / "backend" / "models.py").exists()
            else "",
            "backend/app.py": (ROOT / "backend" / "app.py").read_text(encoding="utf-8")
            if (ROOT / "backend" / "app.py").exists()
            else "",
            "frontend/lib/api.ts": (ROOT / "frontend" / "lib" / "api.ts").read_text(encoding="utf-8")
            if (ROOT / "frontend" / "lib" / "api.ts").exists()
            else "",
            "frontend/app/orders/page.tsx": (ROOT / "frontend" / "app" / "orders" / "page.tsx").read_text(
                encoding="utf-8"
            )
            if (ROOT / "frontend" / "app" / "orders" / "page.tsx").exists()
            else "",
        },
    ),
]


def run(args: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(args, cwd=ROOT, check=True, env=env)


def write_files(files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main() -> None:
    git_dir = ROOT / ".git"
    if git_dir.exists():
        return
    run(["git", "init"])
    run(["git", "config", "user.email", "fixture@aether.dev"])
    run(["git", "config", "user.name", "Aether Fixture"])
    (ROOT / "backend" / "__init__.py").write_text("", encoding="utf-8")
    for stamp, message, files in COMMITS:
        if files:
            write_files(files)
        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
        run(["git", "add", "-A"])
        run(["git", "commit", "-m", message], env=env)


if __name__ == "__main__":
    main()
