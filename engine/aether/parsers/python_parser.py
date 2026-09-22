from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

from aether.ir.models import Contract, Edge, EdgeKind, Node, NodeKind
from aether.parsers.ids import contract_id, module_id, schema_id, symbol_id

ROUTE_DECORATORS = {"get", "post", "put", "patch", "delete", "head", "options"}
TABLE_HINTS = re.compile(
    r"""(?:__tablename__\s*=\s*['\"](\w+)['\"]|Table\(\s*['\"](\w+)['\"])""",
)
ROUTE_HINTS = re.compile(
    r"""@(?:app|router)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]""",
)


@dataclass
class PyExtract:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


def parse_python(path: str, source: str) -> PyExtract:
    extract = _parse_tree_sitter(path, source)
    if extract is None:
        extract = _parse_ast(path, source)
    _augment_with_regex(path, source, extract)
    return extract


def _complexity_text(source: str) -> int:
    return 1 + len(re.findall(r"\b(if|for|while|try|except|and|or)\b", source))


def _parse_ast(path: str, source: str) -> PyExtract:
    out = PyExtract()
    mid = module_id(path)
    loc = source.count("\n") + 1
    out.nodes.append(
        Node(
            id=mid,
            kind=NodeKind.MODULE,
            lang="python",
            path=path,
            export_name=path,
            loc=loc,
            complexity=_complexity_text(source),
        )
    )
    try:
        tree = ast.parse(source)
    except SyntaxError:
        out.nodes[-1].extra["syntax_error"] = True
        return out

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.imports.append(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sid = symbol_id(path, node.name)
            out.nodes.append(
                Node(
                    id=sid,
                    kind=NodeKind.SYMBOL,
                    lang="python",
                    path=path,
                    export_name=node.name,
                    loc=max((node.end_lineno or node.lineno) - node.lineno + 1, 1),
                    complexity=_fn_complexity(node),
                )
            )
            out.edges.append(Edge(src=mid, dst=sid, kind=EdgeKind.IMPORT, weight=0.2))
            route = _fastapi_route(node)
            if route:
                cid = contract_id("http", route)
                out.contracts.append(
                    Contract(id=cid, kind="http", name=route, path=path, lang="python")
                )
                out.nodes.append(
                    Node(
                        id=cid,
                        kind=NodeKind.CONTRACT,
                        lang="python",
                        path=path,
                        export_name=route,
                    )
                )
                out.edges.append(Edge(src=sid, dst=cid, kind=EdgeKind.HTTP, weight=1.5))
        elif isinstance(node, ast.ClassDef):
            sid = symbol_id(path, node.name)
            out.nodes.append(
                Node(
                    id=sid,
                    kind=NodeKind.SYMBOL,
                    lang="python",
                    path=path,
                    export_name=node.name,
                    loc=max((node.end_lineno or node.lineno) - node.lineno + 1, 1),
                    complexity=_fn_complexity(node),
                )
            )
            out.edges.append(Edge(src=mid, dst=sid, kind=EdgeKind.IMPORT, weight=0.2))
            table = _tablename(node)
            if table:
                tid = schema_id(table)
                out.contracts.append(
                    Contract(id=tid, kind="sql", name=table, path=path, lang="python")
                )
                out.nodes.append(
                    Node(
                        id=tid,
                        kind=NodeKind.SCHEMA,
                        lang="python",
                        path=path,
                        export_name=table,
                    )
                )
                out.edges.append(Edge(src=sid, dst=tid, kind=EdgeKind.SQL, weight=2.0))
    return out


def _fn_complexity(node: ast.AST) -> int:
    score = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.BoolOp)):
            score += 1
    return score


def _fastapi_route(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for dec in node.decorator_list:
        call = dec if isinstance(dec, ast.Call) else None
        if call is None:
            continue
        func = call.func
        name = ""
        if isinstance(func, ast.Attribute):
            name = func.attr
        if name not in ROUTE_DECORATORS:
            continue
        if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
            return call.args[0].value
    return None


def _tablename(node: ast.ClassDef) -> str | None:
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        return stmt.value.value
    return None


def _parse_tree_sitter(path: str, source: str) -> PyExtract | None:
    try:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser
    except Exception:
        return None
    try:
        parser = Parser(Language(tspython.language()))
        tree = parser.parse(source.encode("utf-8"))
    except Exception:
        return None
    if tree.root_node.has_error and tree.root_node.child_count == 0:
        return None
    # Tree-sitter walk confirms structure; semantic IR still comes from ast
    # so FastAPI/SQLAlchemy contracts stay accurate. Presence of a successful
    # parse is recorded on the module node after ast extraction.
    extract = _parse_ast(path, source)
    for node in extract.nodes:
        if node.kind == NodeKind.MODULE:
            node.extra["parser"] = "tree-sitter+ast"
    return extract


def _augment_with_regex(path: str, source: str, extract: PyExtract) -> None:
    mid = module_id(path)
    existing = {c.name for c in extract.contracts}
    for match in ROUTE_HINTS.finditer(source):
        route = match.group(2)
        if route in existing:
            continue
        cid = contract_id("http", route)
        extract.contracts.append(
            Contract(id=cid, kind="http", name=route, path=path, lang="python")
        )
        extract.nodes.append(
            Node(id=cid, kind=NodeKind.CONTRACT, lang="python", path=path, export_name=route)
        )
        extract.edges.append(Edge(src=mid, dst=cid, kind=EdgeKind.HTTP, weight=1.2))
        existing.add(route)
    for match in TABLE_HINTS.finditer(source):
        table = match.group(1) or match.group(2)
        if not table or table in existing:
            continue
        tid = schema_id(table)
        extract.contracts.append(
            Contract(id=tid, kind="sql", name=table, path=path, lang="python")
        )
        extract.nodes.append(
            Node(id=tid, kind=NodeKind.SCHEMA, lang="python", path=path, export_name=table)
        )
        extract.edges.append(Edge(src=mid, dst=tid, kind=EdgeKind.SQL, weight=1.8))
        existing.add(table)
