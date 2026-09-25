from pathlib import Path

from aether.ir.models import EdgeKind, NodeKind
from aether.parsers.ids import contract_id
from aether.parsers.go_parser import parse_go
from aether.parsers.java_parser import parse_java
from aether.parsers.python_parser import parse_python
from aether.parsers.typescript_parser import parse_typescript

ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "ir-contract"
HTTP_ORDERS = contract_id("http", "/orders")


def _shape(extract) -> dict:
    return {
        "kinds": sorted(
            n.kind.value
            for n in extract.nodes
            if n.kind in {NodeKind.MODULE, NodeKind.SYMBOL, NodeKind.CONTRACT}
        ),
        "http": sorted(c.name for c in extract.contracts if c.kind == "http"),
        "http_ids": sorted(c.id for c in extract.contracts if c.kind == "http"),
        "http_edge": any(e.kind == EdgeKind.HTTP for e in extract.edges),
    }


def test_python_typescript_go_and_java_share_the_orders_contract():
    extracts = [
        parse_python("app.py", (ROOT / "python" / "app.py").read_text(encoding="utf-8")),
        parse_typescript("api.ts", (ROOT / "typescript" / "api.ts").read_text(encoding="utf-8")),
        parse_go("app.go", (ROOT / "go" / "app.go").read_text(encoding="utf-8")),
        parse_java("OrderController.java", (ROOT / "java" / "OrderController.java").read_text(encoding="utf-8")),
    ]
    shapes = [_shape(extract) for extract in extracts]
    for shape in shapes:
        assert shape["kinds"] == ["contract", "module", "symbol"]
        assert shape["http"] == ["/orders"]
        assert shape["http_ids"] == [HTTP_ORDERS]
        assert shape["http_edge"]
