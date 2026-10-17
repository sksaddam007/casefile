"""Load the generated dataset into FalkorDB in UNWIND batches."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from .db import connect, ensure_schema
from .generator import generate

console = Console()


def _chunk(seq, n=200):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def load(graph_name: str | None = None) -> dict[str, int]:
    g = connect(graph_name)
    ds = generate()

    # fresh start — the demo must be reproducible
    try:
        g.delete()
    except Exception:
        pass  # graph doesn't exist yet on a fresh DB

    for batch in _chunk(ds.accounts):
        g.query("UNWIND $rows AS r CREATE (:Account {id:r.id, name:r.name, country:r.country, tier:r.tier, openedDaysAgo:r.opened_days_ago, flagged:r.flagged})", {"rows": batch})
    for batch in _chunk(ds.devices):
        g.query("UNWIND $rows AS r CREATE (:Device {id:r.id, os:r.os})", {"rows": batch})
    for batch in _chunk(ds.ips):
        g.query("UNWIND $rows AS r CREATE (:Ip {id:r.id, geo:r.geo})", {"rows": batch})
    for batch in _chunk(ds.cards):
        g.query("UNWIND $rows AS r CREATE (:Card {id:r.id, brand:r.brand})", {"rows": batch})
    for batch in _chunk(ds.merchants):
        g.query("UNWIND $rows AS r CREATE (:Merchant {id:r.id, name:r.name, category:r.category})", {"rows": batch})

    for batch in _chunk(ds.uses_device):
        g.query("UNWIND $rows AS r MATCH (a:Account {id:r[0]}), (d:Device {id:r[1]}) CREATE (a)-[:USES_DEVICE]->(d)", {"rows": batch})
    for batch in _chunk(ds.logged_from):
        g.query("UNWIND $rows AS r MATCH (a:Account {id:r[0]}), (i:Ip {id:r[1]}) CREATE (a)-[:LOGGED_FROM]->(i)", {"rows": batch})
    for batch in _chunk(ds.has_card):
        g.query("UNWIND $rows AS r MATCH (a:Account {id:r[0]}), (c:Card {id:r[1]}) CREATE (a)-[:HAS_CARD]->(c)", {"rows": batch})
    for batch in _chunk(ds.transferred):
        g.query(
            "UNWIND $rows AS r MATCH (a:Account {id:r.src}), (b:Account {id:r.dst}) "
            "CREATE (a)-[:TRANSFERRED {id:r.id, amount:r.amount, ts:r.ts, flagged:r.flagged}]->(b)",
            {"rows": batch})
    for batch in _chunk(ds.paid):
        g.query(
            "UNWIND $rows AS r MATCH (a:Account {id:r.src}), (m:Merchant {id:r.dst}) "
            "CREATE (a)-[:PAID {amount:r.amount, ts:r.ts, flagged:r.flagged}]->(m)",
            {"rows": batch})
    for batch in _chunk(ds.alerts):
        g.query(
            "UNWIND $rows AS r MATCH (a:Account {id:r.src}) "
            "CREATE (:Alert {id:r.id, txnId:r.txn_id, amount:r.amount, ts:r.ts, status:r.status, reasons:r.reasons})-[:ON {txn_id:r.txn_id}]->(a)",
            {"rows": batch})

    ensure_schema(g)

    counts = ds.counts()
    table = Table(title="Graph loaded", title_style="bold green")
    table.add_column("What", style="cyan")
    table.add_column("Rows", justify="right", style="yellow")
    for k, v in counts.items():
        table.add_row(k, str(v))
    console.print(table)
    return counts


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else None
    load(name)
