"""FalkorDB connection + schema setup."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()

HOST = os.getenv("FALKORDB_HOST", "localhost")
PORT = int(os.getenv("FALKORDB_PORT", "6380"))  # host port (6379 is taken by another local redis)
GRAPH_NAME = os.getenv("FALKORDB_GRAPH", "bank")


def connect(database: str | None = None):
    db = FalkorDB(host=HOST, port=PORT)
    return db.select_graph(database or GRAPH_NAME)


INDICES = [
    "CREATE INDEX FOR (:Alert) ON (a.id)",  # placeholder replaced below
]


def ensure_schema(g) -> None:
    """Indices on every property the agent's tools match on."""
    statements = [
        "CREATE INDEX FOR (a:Alert) ON (a.id)",
        "CREATE INDEX FOR (a:Alert) ON (a.status)",
        "CREATE INDEX FOR (n:Account) ON (n.id)",
        "CREATE INDEX FOR (n:Device) ON (n.id)",
        "CREATE INDEX FOR (n:Ip) ON (n.id)",
        "CREATE INDEX FOR (n:Card) ON (n.id)",
        "CREATE INDEX FOR (m:Merchant) ON (m.id)",
        "CREATE INDEX FOR (t:Txn) ON (t.id)",
    ]
    for q in statements:
        try:
            g.query(q)
        except Exception as e:  # index may already exist
            if "already indexed" not in str(e):
                raise
