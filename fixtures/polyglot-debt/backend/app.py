from fastapi import FastAPI

from backend.models import Order, User

app = FastAPI(title="polyglot-debt")

USERS = [User(id=1, email="ada@example.com")]
ORDERS = [
    Order(id=1, user_id=1, total=19.0, status="open", metadata={"note": "first"}),
    Order(id=2, user_id=1, total=44.0, status="paid", metadata={"source": "web", "blob": "x" * 32}),
]


@app.get("/users")
def list_users() -> list[User]:
    return USERS


@app.get("/orders")
def list_orders() -> list[Order]:
    # Unbounded list — no limit/cursor. Frontend fetches the whole table.
    return ORDERS


@app.get("/orders/{order_id}")
def get_order(order_id: int) -> Order:
    for order in ORDERS:
        if order.id == order_id:
            return order
    raise KeyError(order_id)
