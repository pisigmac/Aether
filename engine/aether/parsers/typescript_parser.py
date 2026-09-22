from __future__ import annotations

import re
from dataclasses import dataclass, field

from aether.ir.models import Contract, Edge, EdgeKind, Node, NodeKind
from aether.parsers.ids import contract_id, module_id, symbol_id

IMPORT_RE = re.compile(
    r"""import\s+(?:type\s+)?(?:[\w*\s{},]+)\s+from\s+['\"]([^'\"]+)['\"]"""
)
FETCH_RE = re.compile(
    r"""(?:fetch|axios\.(?:get|post|put|patch|delete)|\$fetch)\(\s*['"`]([^'"`]+)['"`]"""
)
EXPORT_FN_RE = re.compile(
    r"""(?:export\s+)?(?:async\s+)?function\s+(\w+)|export\s+const\s+(\w+)\s*="""
)
EXPORT_CLASS_RE = re.compile(r"""(?:export\s+)?class\s+(\w+)""")


@dataclass
class TsExtract:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


def parse_typescript(path: str, source: str) -> TsExtract:
    extract = _parse_tree_sitter(path, source)
    if extract is None:
        extract = _parse_regex(path, source)
    else:
        _harvest_regex_contracts(path, source, extract)
    return extract


def _complexity_text(source: str) -> int:
    return 1 + len(re.findall(r"\b(if|for|while|try|catch|&&|\|\||\?)\b", source))


def _parse_regex(path: str, source: str) -> TsExtract:
    out = TsExtract()
    mid = module_id(path)
    loc = source.count("\n") + 1
    out.nodes.append(
        Node(
            id=mid,
            kind=NodeKind.MODULE,
            lang="typescript",
            path=path,
            export_name=path,
            loc=loc,
            complexity=_complexity_text(source),
            extra={"parser": "regex"},
        )
    )
    out.imports.extend(m.group(1) for m in IMPORT_RE.finditer(source))
    for match in EXPORT_FN_RE.finditer(source):
        name = match.group(1) or match.group(2)
        if not name:
            continue
        sid = symbol_id(path, name)
        out.nodes.append(
            Node(id=sid, kind=NodeKind.SYMBOL, lang="typescript", path=path, export_name=name)
        )
        out.edges.append(Edge(src=mid, dst=sid, kind=EdgeKind.IMPORT, weight=0.2))
    for match in EXPORT_CLASS_RE.finditer(source):
        name = match.group(1)
        sid = symbol_id(path, name)
        out.nodes.append(
            Node(id=sid, kind=NodeKind.SYMBOL, lang="typescript", path=path, export_name=name)
        )
        out.edges.append(Edge(src=mid, dst=sid, kind=EdgeKind.IMPORT, weight=0.2))
    _harvest_regex_contracts(path, source, out)
    return out


def _harvest_regex_contracts(path: str, source: str, extract: TsExtract) -> None:
    mid = module_id(path)
    seen = {c.name for c in extract.contracts}
    for match in FETCH_RE.finditer(source):
        url = match.group(1)
        route = _normalize_url(url)
        if not route or route in seen:
            continue
        cid = contract_id("http", route)
        extract.contracts.append(
            Contract(id=cid, kind="http", name=route, path=path, lang="typescript", detail=url)
        )
        extract.nodes.append(
            Node(id=cid, kind=NodeKind.CONTRACT, lang="typescript", path=path, export_name=route)
        )
        extract.edges.append(Edge(src=mid, dst=cid, kind=EdgeKind.HTTP, weight=1.5))
        seen.add(route)


def _normalize_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            return parsed.path or url
        except Exception:
            return url
    if url.startswith("`"):
        return ""
    return url.split("?")[0]


def _parse_tree_sitter(path: str, source: str) -> TsExtract | None:
    try:
        import tree_sitter_typescript as tstypescript
        from tree_sitter import Language, Parser
    except Exception:
        return None
    try:
        lang_fn = (
            tstypescript.language_tsx if path.endswith((".tsx", ".jsx")) else tstypescript.language_typescript
        )
        parser = Parser(Language(lang_fn()))
        tree = parser.parse(source.encode("utf-8"))
    except Exception:
        return None

    out = TsExtract()
    mid = module_id(path)
    loc = source.count("\n") + 1
    out.nodes.append(
        Node(
            id=mid,
            kind=NodeKind.MODULE,
            lang="typescript",
            path=path,
            export_name=path,
            loc=loc,
            complexity=_complexity_text(source),
            extra={"parser": "tree-sitter"},
        )
    )
    src_bytes = source.encode("utf-8")

    def text(node) -> str:
        return src_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")

    def walk(node) -> None:
        t = node.type
        if t == "import_statement":
            for child in node.children:
                if child.type in {"string", "string_fragment"}:
                    raw = text(child).strip("'\"")
                    if raw:
                        out.imports.append(raw)
        elif t in {"function_declaration", "function_signature", "method_definition"}:
            name_node = node.child_by_field_name("name")
            if name_node:
                name = text(name_node)
                sid = symbol_id(path, name)
                out.nodes.append(
                    Node(
                        id=sid,
                        kind=NodeKind.SYMBOL,
                        lang="typescript",
                        path=path,
                        export_name=name,
                    )
                )
                out.edges.append(Edge(src=mid, dst=sid, kind=EdgeKind.IMPORT, weight=0.2))
        elif t == "class_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = text(name_node)
                sid = symbol_id(path, name)
                out.nodes.append(
                    Node(
                        id=sid,
                        kind=NodeKind.SYMBOL,
                        lang="typescript",
                        path=path,
                        export_name=name,
                    )
                )
                out.edges.append(Edge(src=mid, dst=sid, kind=EdgeKind.IMPORT, weight=0.2))
        elif t == "call_expression":
            fn = node.child_by_field_name("function")
            args = node.child_by_field_name("arguments")
            if fn is not None and args is not None:
                fn_text = text(fn)
                if "fetch" in fn_text or "axios" in fn_text:
                    arg_text = text(args)
                    m = re.search(r"""['"`]([^'"`]+)['"`]""", arg_text)
                    if m:
                        route = _normalize_url(m.group(1))
                        if route:
                            cid = contract_id("http", route)
                            if cid not in {c.id for c in out.contracts}:
                                out.contracts.append(
                                    Contract(
                                        id=cid,
                                        kind="http",
                                        name=route,
                                        path=path,
                                        lang="typescript",
                                    )
                                )
                                out.nodes.append(
                                    Node(
                                        id=cid,
                                        kind=NodeKind.CONTRACT,
                                        lang="typescript",
                                        path=path,
                                        export_name=route,
                                    )
                                )
                                out.edges.append(
                                    Edge(src=mid, dst=cid, kind=EdgeKind.HTTP, weight=1.5)
                                )
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return out
