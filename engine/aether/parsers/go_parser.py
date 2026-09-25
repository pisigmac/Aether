from __future__ import annotations

import re
from dataclasses import dataclass, field

from aether.ir.models import Contract, Edge, EdgeKind, Node, NodeKind
from aether.parsers.ids import contract_id, module_id, symbol_id

HTTP_FUNCS = {
    "HandleFunc",
    "Handle",
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "Get",
    "Post",
    "Put",
    "Patch",
    "Delete",
}
FUNC_RE = re.compile(r"(?m)^func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(")
HANDLE_RE = re.compile(
    r"""(?:HandleFunc|Handle|\.(?:GET|POST|PUT|PATCH|DELETE|Get|Post|Put|Patch|Delete))\(\s*"(/[^"]*)\""""
)


@dataclass
class GoExtract:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


def parse_go(path: str, source: str) -> GoExtract:
    extract = _parse_tree_sitter(path, source)
    if extract is None:
        extract = _parse_regex(path, source)
    return extract


def _complexity_text(source: str) -> int:
    return 1 + len(re.findall(r"\b(if|for|switch|select|&&|\|\|)\b", source))


def _parse_regex(path: str, source: str) -> GoExtract:
    out = GoExtract()
    mid = module_id(path)
    out.nodes.append(
        Node(
            id=mid,
            kind=NodeKind.MODULE,
            lang="go",
            path=path,
            export_name=path,
            loc=source.count("\n") + 1,
            complexity=_complexity_text(source),
            extra={"parser": "regex"},
        )
    )
    for match in FUNC_RE.finditer(source):
        _add_symbol(out, path, mid, match.group(1))
    _add_routes(out, path, mid, source)
    return out


def _parse_tree_sitter(path: str, source: str) -> GoExtract | None:
    try:
        import tree_sitter_go as tsgo
        from tree_sitter import Language, Parser
    except Exception:
        return None
    try:
        parser = Parser(Language(tsgo.language()))
        tree = parser.parse(source.encode("utf-8"))
    except Exception:
        return None
    if tree.root_node.has_error and tree.root_node.child_count == 0:
        return None

    out = GoExtract()
    mid = module_id(path)
    src = source.encode("utf-8")
    out.nodes.append(
        Node(
            id=mid,
            kind=NodeKind.MODULE,
            lang="go",
            path=path,
            export_name=path,
            loc=source.count("\n") + 1,
            complexity=_complexity_text(source),
            extra={"parser": "tree-sitter"},
        )
    )

    def text(node) -> str:
        return src[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")

    def walk(node, owner: str) -> None:
        if node.type == "import_spec":
            for child in node.children:
                if child.type == "interpreted_string_literal":
                    for part in child.children:
                        if part.type == "interpreted_string_literal_content":
                            spec = text(part).strip()
                            if spec:
                                out.imports.append(spec)
            return
        if node.type in {"function_declaration", "method_declaration"}:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                sid = _add_symbol(out, path, mid, text(name_node))
                for child in node.children:
                    walk(child, sid)
            return
        if node.type == "call_expression":
            fn = node.child_by_field_name("function")
            args = node.child_by_field_name("arguments")
            if fn is not None and args is not None:
                fn_text = text(fn)
                name = fn_text.rsplit(".", 1)[-1]
                if name in HTTP_FUNCS:
                    route = _first_route(text(args))
                    if route:
                        _add_contract(out, path, owner, route)
        for child in node.children:
            walk(child, owner)

    walk(tree.root_node, mid)
    return out


def _add_symbol(out: GoExtract, path: str, mid: str, name: str) -> str:
    sid = symbol_id(path, name)
    if sid not in {n.id for n in out.nodes}:
        out.nodes.append(
            Node(id=sid, kind=NodeKind.SYMBOL, lang="go", path=path, export_name=name)
        )
        out.edges.append(Edge(src=mid, dst=sid, kind=EdgeKind.IMPORT, weight=0.2))
    return sid


def _add_contract(out: GoExtract, path: str, src: str, route: str) -> None:
    cid = contract_id("http", route)
    if cid in {c.id for c in out.contracts}:
        return
    out.contracts.append(Contract(id=cid, kind="http", name=route, path=path, lang="go"))
    out.nodes.append(
        Node(id=cid, kind=NodeKind.CONTRACT, lang="go", path=path, export_name=route)
    )
    out.edges.append(Edge(src=src, dst=cid, kind=EdgeKind.HTTP, weight=1.5))


def _add_routes(out: GoExtract, path: str, mid: str, source: str) -> None:
    for match in HANDLE_RE.finditer(source):
        _add_contract(out, path, mid, match.group(1))


def _first_route(args: str) -> str:
    match = re.search(r'"(/[^"]*)"', args)
    return match.group(1) if match else ""
