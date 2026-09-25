from aether.ir.models import Node, NodeKind, Snapshot
from aether.parsers.indexes import parse_prisma, parse_sql
from aether.parsers.python_parser import parse_python
from aether.physics.metrics import detect_patterns


def _schema(extract, name: str):
    return next(n for n in extract.nodes if n.kind == NodeKind.SCHEMA and n.export_name == name)


def test_table_without_lookup_is_not_a_missing_index():
    src = '''
class Note:
    __tablename__ = "notes"
    id: int
    body: str
'''
    node = _schema(parse_python("models.py", src), "notes")
    assert node.extra["missing_index"] is False


def test_sqlalchemy_foreign_key_without_index_is_missing():
    src = '''
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

class Order:
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

def load(session):
    return session.query(Order).filter(Order.user_id == 1)
'''
    node = _schema(parse_python("models.py", src), "orders")
    assert node.extra["missing_index"] is True
    assert "user_id" in node.extra["lookups"]
    assert "id" in node.extra["indexed"]


def test_sqlalchemy_index_covers_the_lookup():
    src = '''
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

class Order:
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_user", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

def load(session):
    return session.query(Order).filter(Order.user_id == 1)
'''
    node = _schema(parse_python("models.py", src), "orders")
    assert node.extra["missing_index"] is False


def test_prisma_relation_without_index_is_missing():
    src = '''
model Order {
  id     Int  @id
  userId Int
  user   User @relation(fields: [userId], references: [id])
}
'''
    node = _schema(parse_prisma("schema.prisma", src), "Order")
    assert node.extra["missing_index"] is True
    assert node.extra["lookups"] == ["userId"]


def test_prisma_index_covers_the_relation():
    src = '''
model Order {
  id     Int  @id
  userId Int
  user   User @relation(fields: [userId], references: [id])
  @@index([userId])
  @@map("orders")
}
'''
    node = _schema(parse_prisma("schema.prisma", src), "orders")
    assert node.extra["missing_index"] is False


def test_sql_where_without_index_is_missing():
    src = '''
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  user_id INTEGER
);
SELECT * FROM orders WHERE user_id = 1;
'''
    node = _schema(parse_sql("schema.sql", src), "orders")
    assert node.extra["missing_index"] is True


def test_sql_create_index_covers_the_where():
    src = '''
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  user_id INTEGER
);
CREATE INDEX ix_orders_user ON orders (user_id);
SELECT * FROM orders WHERE user_id = 1;
'''
    node = _schema(parse_sql("schema.sql", src), "orders")
    assert node.extra["missing_index"] is False


def test_pattern_label_follows_the_flag_not_the_schema():
    plain = Node(id="sch", kind=NodeKind.SCHEMA, export_name="orders")
    flagged = plain.model_copy(update={"extra": {"missing_index": True}})
    bare = Snapshot(commit_sha="a", authored_at="2026-01-01T00:00:00+00:00", snapshot_hash="a", nodes=[plain])
    marked = bare.model_copy(update={"nodes": [flagged]})
    assert "missing_index" not in detect_patterns(bare)
    assert "missing_index" in detect_patterns(marked)
