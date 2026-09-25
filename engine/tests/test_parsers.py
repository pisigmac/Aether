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


def test_go_emits_handlefunc_contract():
    src = '''
package orders

import "net/http"

func listOrders(w http.ResponseWriter, r *http.Request) {
    http.HandleFunc("/orders", listOrders)
}
'''
    from aether.parsers.go_parser import parse_go

    extract = parse_go("app.go", src)
    module = next(n for n in extract.nodes if n.kind == NodeKind.MODULE)
    assert module.extra.get("parser") == "tree-sitter"
    assert any(c.name == "/orders" and c.lang == "go" for c in extract.contracts)
    assert any(n.kind == NodeKind.SYMBOL and n.export_name == "listOrders" for n in extract.nodes)


def test_java_emits_getmapping_contract():
    src = '''
package orders;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class OrderController {
    @GetMapping("/orders")
    public String listOrders() {
        return "ok";
    }
}
'''
    from aether.parsers.java_parser import parse_java

    extract = parse_java("OrderController.java", src)
    module = next(n for n in extract.nodes if n.kind == NodeKind.MODULE)
    assert module.extra.get("parser") == "tree-sitter"
    assert any(c.name == "/api/orders" and c.lang == "java" for c in extract.contracts)
    assert any(n.kind == NodeKind.SYMBOL and n.export_name == "listOrders" for n in extract.nodes)


def test_typescript_emits_fetch_contract():
    src = '''
export async function fetchOrders() {
  return fetch("/orders");
}
'''
    extract = parse_typescript("frontend/lib/api.ts", src)
    assert any(c.name == "/orders" for c in extract.contracts)
    assert all(n.kind.value != "unknown" for n in extract.nodes)
