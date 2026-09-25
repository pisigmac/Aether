from __future__ import annotations

import re
from dataclasses import dataclass, field

from aether.ir.models import Contract, Edge, EdgeKind, Node, NodeKind
from aether.parsers.ids import contract_id, module_id, symbol_id

MAPPING = {
    "GetMapping",
    "PostMapping",
    "PutMapping",
    "PatchMapping",
    "DeleteMapping",
    "RequestMapping",
    "Path",
}
METHOD_RE = re.compile(r"(?m)(?:public|protected|private)\s+[\w<>\[\]]+\s+(\w+)\s*\(")
MAP_RE = re.compile(
    r"""@(?:GetMapping|PostMapping|PutMapping|PatchMapping|DeleteMapping|RequestMapping|Path)\s*\(\s*(?:(?:value|path)\s*=\s*)?"(/[^"]*)\""""
)


@dataclass
class JavaExtract:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


def parse_java(path: str, source: str) -> JavaExtract:
    extract = _parse_tree_sitter(path, source)
    if extract is None:
        extract = _parse_regex(path, source)
    return extract


def _complexity_text(source: str) -> int:
    return 1 + len(re.findall(r"\b(if|for|while|switch|catch|&&|\|\|)\b", source))


def _parse_regex(path: str, source: str) -> JavaExtract:
    out = JavaExtract()
    mid = module_id(path)
    out.nodes.append(
        Node(
            id=mid,
            kind=NodeKind.MODULE,
            lang="java",
            path=path,
            export_name=path,
            loc=source.count("\n") + 1,
            complexity=_complexity_text(source),
            extra={"parser": "regex"},
        )
    )
    for match in METHOD_RE.finditer(source):
        _add_symbol(out, path, mid, match.group(1))
    for match in MAP_RE.finditer(source):
        _add_contract(out, path, mid, match.group(1))
    return out


def _parse_tree_sitter(path: str, source: str) -> JavaExtract | None:
    try:
        import tree_sitter_java as tsjava
        from tree_sitter import Language, Parser
    except Exception:
        return None
    try:
        parser = Parser(Language(tsjava.language()))
        tree = parser.parse(source.encode("utf-8"))
    except Exception:
        return None
    if tree.root_node.has_error and tree.root_node.child_count == 0:
        return None

    out = JavaExtract()
    mid = module_id(path)
    src = source.encode("utf-8")
    out.nodes.append(
        Node(
            id=mid,
            kind=NodeKind.MODULE,
            lang="java",
            path=path,
            export_name=path,
            loc=source.count("\n") + 1,
            complexity=_complexity_text(source),
            extra={"parser": "tree-sitter"},
        )
    )

    def text(node) -> str:
        return src[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")

    def walk(node, prefix: str) -> None:
        if node.type == "import_declaration":
            for child in node.children:
                if child.type == "scoped_identifier":
                    spec = text(child).strip()
                    if spec:
                        out.imports.append(spec)
            return
        if node.type == "class_declaration":
            routes = _annotation_routes(_modifiers(node), text)
            class_prefix = _join(prefix, routes[0]) if routes else prefix
            body = node.child_by_field_name("body")
            if body is not None:
                for child in body.children:
                    walk(child, class_prefix)
            return
        if node.type == "method_declaration":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                sid = _add_symbol(out, path, mid, text(name_node))
                for route in _annotation_routes(_modifiers(node), text):
                    _add_contract(out, path, sid, _join(prefix, route))
            return
        for child in node.children:
            walk(child, prefix)

    walk(tree.root_node, "")
    return out


def _modifiers(node):
    for child in node.children:
        if child.type == "modifiers":
            return child
    return None


def _annotation_routes(node, text) -> list[str]:
    if node is None:
        return []
    routes: list[str] = []

    def visit(current) -> None:
        if current.type == "annotation":
            name = current.child_by_field_name("name")
            if name is not None and text(name) in MAPPING:
                route = _route_from_args(current.child_by_field_name("arguments"), text)
                if route:
                    routes.append(route)
            return
        for child in current.children:
            visit(child)

    visit(node)
    return routes


def _route_from_args(args, text) -> str:
    if args is None:
        return ""
    for child in args.children:
        if child.type == "string_literal":
            return _unquote(text(child))
        if child.type != "element_value_pair":
            continue
        key = next((part for part in child.children if part.type == "identifier"), None)
        lit = next((part for part in child.children if part.type == "string_literal"), None)
        if lit is None or key is None:
            continue
        if text(key) in {"value", "path"}:
            return _unquote(text(lit))
    return ""


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def _join(prefix: str, route: str) -> str:
    prefix = prefix.strip()
    route = route.strip()
    if not prefix:
        return route if route.startswith("/") else f"/{route}"
    if not route:
        return prefix if prefix.startswith("/") else f"/{prefix}"
    return "/" + f"{prefix.strip('/')}/{route.strip('/')}"


def _add_symbol(out: JavaExtract, path: str, mid: str, name: str) -> str:
    sid = symbol_id(path, name)
    if sid not in {n.id for n in out.nodes}:
        out.nodes.append(
            Node(id=sid, kind=NodeKind.SYMBOL, lang="java", path=path, export_name=name)
        )
        out.edges.append(Edge(src=mid, dst=sid, kind=EdgeKind.IMPORT, weight=0.2))
    return sid


def _add_contract(out: JavaExtract, path: str, src: str, route: str) -> None:
    if not route.startswith("/"):
        route = f"/{route}"
    cid = contract_id("http", route)
    if cid in {c.id for c in out.contracts}:
        return
    out.contracts.append(Contract(id=cid, kind="http", name=route, path=path, lang="java"))
    out.nodes.append(
        Node(id=cid, kind=NodeKind.CONTRACT, lang="java", path=path, export_name=route)
    )
    out.edges.append(Edge(src=src, dst=cid, kind=EdgeKind.HTTP, weight=1.5))
