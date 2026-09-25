from aether.ir.models import Contract, EdgeKind, Node, NodeKind
from aether.parsers.contracts import link_contracts, load_openapi
from aether.parsers.ids import contract_id


def _http(name: str, lang: str) -> tuple[Node, Contract]:
    cid = contract_id("http", name)
    return (
        Node(id=cid, kind=NodeKind.CONTRACT, lang=lang, export_name=name),
        Contract(id=cid, kind="http", name=name, lang=lang),
    )


def _bind(openapi: dict | None = None):
    py_node, py_contract = _http("/orders", "python")
    ts_node, ts_contract = _http("/orders", "typescript")
    nodes, edges, contracts = link_contracts(
        [py_node, ts_node],
        [],
        [py_contract, ts_contract],
        openapi,
    )
    return nodes, edges, contracts


def test_name_match_when_no_spec():
    _nodes, edges, _contracts = _bind(None)
    http = [e for e in edges if e.kind == EdgeKind.HTTP and e.weight == 2.5]
    assert http
    assert not any(e.kind == EdgeKind.UNRESOLVED for e in edges)


def test_unresolved_when_names_differ_and_no_spec():
    _py_node, py_contract = _http("/orders", "python")
    ts_node, ts_contract = _http("/health", "typescript")
    _nodes, edges, _contracts = link_contracts([ts_node], [], [py_contract, ts_contract], None)
    assert any(e.kind == EdgeKind.UNRESOLVED and e.src == ts_node.id for e in edges)
    assert not any(e.kind == EdgeKind.HTTP and e.weight == 2.5 for e in edges)


def test_openapi_exact_path_outranks_name_match():
    nodes, edges, _contracts = _bind({"paths": {"/orders": {"get": {}}}})
    cid = contract_id("http", "/orders")
    assert any(e.src == cid and e.dst == cid and e.kind == EdgeKind.HTTP and e.weight == 3.0 for e in edges)
    assert not any(e.weight == 2.5 for e in edges)
    assert any(n.id == cid and n.extra.get("openapi") is True for n in nodes)


def test_openapi_template_binds_concrete_fetch():
    ts_node, ts_contract = _http("/orders/9", "typescript")
    nodes, edges, contracts = link_contracts(
        [ts_node],
        [],
        [ts_contract],
        {"paths": {"/orders/{id}": {"get": {}}}},
    )
    spec = contract_id("http", "/orders/{id}")
    assert any(n.id == spec and n.extra.get("source") == "openapi" for n in nodes)
    assert any(e.src == ts_node.id and e.dst == spec and e.kind == EdgeKind.HTTP and e.weight == 3.0 for e in edges)
    assert not any(e.kind == EdgeKind.UNRESOLVED for e in edges)
    assert any(c.name == "/orders/{id}" and c.detail == "openapi" for c in contracts)


def test_name_match_is_fallback_when_spec_misses_the_fetch():
    _nodes, edges, _contracts = _bind({"paths": {"/other": {"get": {}}}})
    cid = contract_id("http", "/orders")
    assert any(e.src == cid and e.dst == cid and e.kind == EdgeKind.HTTP and e.weight == 2.5 for e in edges)
    assert not any(e.weight == 3.0 and e.dst == cid for e in edges)


def test_unresolved_when_spec_and_names_both_miss():
    ts_node, ts_contract = _http("/missing", "typescript")
    _nodes, edges, _contracts = link_contracts(
        [ts_node],
        [],
        [ts_contract],
        {"paths": {"/orders": {"get": {}}}},
    )
    assert any(e.kind == EdgeKind.UNRESOLVED and e.src == ts_node.id for e in edges)
    assert not any(e.src == ts_node.id and e.kind == EdgeKind.HTTP and e.weight == 3.0 for e in edges)


def test_load_openapi_reads_first_valid_json(tmp_path):
    (tmp_path / "openapi.json").write_text("{", encoding="utf-8")
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "openapi.json").write_text('{"paths": {"/orders": {}}}', encoding="utf-8")

    def show(root, rel, _sha):
        file = root / rel
        return file.read_text(encoding="utf-8") if file.is_file() else ""

    doc = load_openapi(tmp_path, show, None)
    assert doc == {"paths": {"/orders": {}}}
