from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

from aether.ir.models import Contract, Edge, Node, NodeKind
from aether.parsers.ids import schema_id

QUERY_CALLS = {"filter", "filter_by", "where", "order_by", "join"}
MODEL_RE = re.compile(r"model\s+(\w+)\s*\{([^}]*)\}", re.S)
CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[\w\"]+\.)?[\"]?(\w+)[\"]?\s*\((.*?)\)\s*;",
    re.I | re.S,
)
CREATE_INDEX_RE = re.compile(
    r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+\w+\s+ON\s+(?:[\w\"]+\.)?[\"]?(\w+)[\"]?\s*\(([^)]*)\)",
    re.I,
)
WHERE_RE = re.compile(r"\bFROM\s+(\w+)\b(?:\s+(?:AS\s+)?(\w+))?[\s\S]{0,200}?\bWHERE\s+(\w+)", re.I)
JOIN_RE = re.compile(r"\bJOIN\s+(\w+)\b(?:\s+(?:AS\s+)?(\w+))?\s+ON\s+(\w+)\.(\w+)", re.I)


@dataclass
class Evidence:
    indexed: set[str] = field(default_factory=set)
    lookups: set[str] = field(default_factory=set)

    @property
    def missing(self) -> bool:
        return bool(self.lookups - self.indexed)


@dataclass
class IndexExtract:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


def apply_sqlalchemy(source: str, extract) -> None:
    found = sqlalchemy_evidence(source)
    for node in extract.nodes:
        if node.kind != NodeKind.SCHEMA:
            continue
        evidence = found.get(node.export_name, Evidence())
        _stamp(node, evidence)


def parse_prisma(path: str, source: str) -> IndexExtract:
    return _from_evidence(path, "prisma", prisma_evidence(source))


def parse_sql(path: str, source: str) -> IndexExtract:
    return _from_evidence(path, "sql", sql_evidence(source))


def sqlalchemy_evidence(source: str) -> dict[str, Evidence]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    tables: dict[str, str] = {}
    columns: dict[str, set[str]] = {}
    found: dict[str, Evidence] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            table = _tablename(node)
            if not table:
                continue
            tables[node.name] = table
            evidence = found.setdefault(table, Evidence())
            cols: set[str] = set()
            for stmt in node.body:
                _read_table_args(stmt, evidence)
                col = _assigned_name(stmt)
                if not col or col.startswith("_"):
                    continue
                cols.add(col)
                if _marked(stmt, "primary_key") or _marked(stmt, "index") or _marked(stmt, "unique"):
                    evidence.indexed.add(col)
                if _has_call(stmt, "ForeignKey"):
                    evidence.lookups.add(col)
            columns[table] = cols
        elif isinstance(node, ast.Call) and _call_name(node) == "Table":
            _read_table_call(node, found)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) not in QUERY_CALLS:
            continue
        name = _call_name(node)
        if name == "filter_by":
            keys = {kw.arg for kw in node.keywords if kw.arg}
            for table, cols in columns.items():
                for key in keys & cols:
                    found[table].lookups.add(key)
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Attribute) or not isinstance(child.value, ast.Name):
                continue
            table = tables.get(child.value.id)
            if table:
                found[table].lookups.add(child.attr)
    return found


def prisma_evidence(source: str) -> dict[str, Evidence]:
    found: dict[str, Evidence] = {}
    for match in MODEL_RE.finditer(source):
        body = match.group(2)
        table = match.group(1)
        mapped = re.search(r'@@map\(\s*"(\w+)"\s*\)', body)
        if mapped:
            table = mapped.group(1)
        evidence = found.setdefault(table, Evidence())
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("@@"):
                continue
            field = stripped.split()[0]
            if field.startswith("@"):
                continue
            if re.search(r"@(id|unique)\b", stripped):
                evidence.indexed.add(field)
        for block in re.finditer(r"@@(?:index|unique|id)\(\s*\[([^\]]*)\]", body):
            evidence.indexed.update(_names(block.group(1)))
        for block in re.finditer(r"@relation\([^)]*fields:\s*\[([^\]]*)\]", body):
            evidence.lookups.update(_names(block.group(1)))
    return found


def sql_evidence(source: str) -> dict[str, Evidence]:
    found: dict[str, Evidence] = {}
    for match in CREATE_TABLE_RE.finditer(source):
        table = match.group(1)
        evidence = found.setdefault(table, Evidence())
        body = match.group(2)
        for part in _split_sql_list(body):
            piece = part.strip()
            if not piece:
                continue
            upper = piece.upper()
            if upper.startswith("PRIMARY KEY"):
                evidence.indexed.update(_paren_names(piece))
                continue
            if upper.startswith("UNIQUE"):
                evidence.indexed.update(_paren_names(piece))
                continue
            if upper.startswith("FOREIGN KEY"):
                evidence.lookups.update(_paren_names(piece))
                continue
            col = piece.split()[0].strip('"')
            if not col or col.upper() in {"CONSTRAINT"}:
                continue
            if "PRIMARY KEY" in upper or re.search(r"\bUNIQUE\b", upper):
                evidence.indexed.add(col)
            if "REFERENCES" in upper:
                evidence.lookups.add(col)
    for match in CREATE_INDEX_RE.finditer(source):
        evidence = found.setdefault(match.group(1), Evidence())
        evidence.indexed.update(_names(match.group(2)))
    for match in WHERE_RE.finditer(source):
        table = match.group(1)
        evidence = found.setdefault(table, Evidence())
        column = match.group(3)
        if column.lower() != table.lower():
            evidence.lookups.add(column)
    for match in JOIN_RE.finditer(source):
        evidence = found.setdefault(match.group(1), Evidence())
        evidence.lookups.add(match.group(4))
    return found


def _from_evidence(path: str, lang: str, found: dict[str, Evidence]) -> IndexExtract:
    out = IndexExtract()
    for table, evidence in found.items():
        tid = schema_id(table)
        node = Node(
            id=tid,
            kind=NodeKind.SCHEMA,
            lang=lang,
            path=path,
            export_name=table,
        )
        _stamp(node, evidence)
        out.nodes.append(node)
        out.contracts.append(Contract(id=tid, kind="sql", name=table, path=path, lang=lang))
    return out


def _stamp(node: Node, evidence: Evidence) -> None:
    node.extra["indexed"] = sorted(evidence.indexed)
    node.extra["lookups"] = sorted(evidence.lookups)
    node.extra["missing_index"] = evidence.missing


def _tablename(node: ast.ClassDef) -> str | None:
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__tablename__":
                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        return stmt.value.value
    return None


def _assigned_name(stmt: ast.stmt) -> str | None:
    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        return stmt.target.id
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        return stmt.targets[0].id
    return None


def _read_table_args(stmt: ast.stmt, evidence: Evidence) -> None:
    if not isinstance(stmt, ast.Assign):
        return
    if not any(isinstance(t, ast.Name) and t.id == "__table_args__" for t in stmt.targets):
        return
    for call in ast.walk(stmt.value):
        if isinstance(call, ast.Call) and _call_name(call) == "Index":
            evidence.indexed.update(_index_columns(call))


def _read_table_call(node: ast.Call, found: dict[str, Evidence]) -> None:
    if not node.args or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
        return
    evidence = found.setdefault(node.args[0].value, Evidence())
    for arg in node.args[1:]:
        if not isinstance(arg, ast.Call):
            continue
        name = _call_name(arg)
        if name == "Index":
            evidence.indexed.update(_index_columns(arg))
        elif name == "Column" and arg.args and isinstance(arg.args[0], ast.Constant):
            col = arg.args[0].value
            if not isinstance(col, str):
                continue
            if _marked(arg, "primary_key") or _marked(arg, "index") or _marked(arg, "unique"):
                evidence.indexed.add(col)
            if _has_call(arg, "ForeignKey"):
                evidence.lookups.add(col)


def _index_columns(call: ast.Call) -> set[str]:
    cols: set[str] = set()
    for arg in call.args[1:]:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            cols.add(arg.value)
        elif isinstance(arg, ast.Attribute):
            cols.add(arg.attr)
    return cols


def _marked(node: ast.AST, keyword: str) -> bool:
    for call in ast.walk(node):
        if not isinstance(call, ast.Call):
            continue
        for item in call.keywords:
            if item.arg == keyword and isinstance(item.value, ast.Constant) and item.value.value is True:
                return True
    return False


def _has_call(node: ast.AST, name: str) -> bool:
    return any(isinstance(call, ast.Call) and _call_name(call) == name for call in ast.walk(node))


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _names(text: str) -> set[str]:
    return {part.strip().strip('"') for part in text.split(",") if part.strip()}


def _paren_names(text: str) -> set[str]:
    match = re.search(r"\(([^)]*)\)", text)
    return _names(match.group(1)) if match else set()


def _split_sql_list(body: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for i, char in enumerate(body):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif char == "," and depth == 0:
            parts.append(body[start:i])
            start = i + 1
    parts.append(body[start:])
    return parts
