from aether.ir.models import NodeKind
from aether.parsers.python_parser import parse_python
from aether.parsers.typescript_parser import parse_typescript


def test_python_emits_route_and_schema():
    src = '''
from fastapi import FastAPI
app = FastAPI()

class Order:
    __tablename__ = "orders"

@app.get("/orders")
def list_orders():
    return []
'''
    extract = parse_python("backend/app.py", src)
    kinds = {n.kind for n in extract.nodes}
    assert NodeKind.MODULE in kinds
    assert NodeKind.CONTRACT in kinds
    assert NodeKind.SCHEMA in kinds
    assert any(c.name == "/orders" for c in extract.contracts)


def test_typescript_emits_fetch_contract():
    src = '''
export async function fetchOrders() {
  return fetch("/orders");
}
'''
    extract = parse_typescript("frontend/lib/api.ts", src)
    assert any(c.name == "/orders" for c in extract.contracts)
    assert all(n.kind.value != "unknown" for n in extract.nodes)
