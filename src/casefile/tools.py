"""The graph tools the agent can pick from.

Each tool = one Cypher query the LLM decides to call, with real
parameters. The agent NEVER invents data — every fact comes from a
traversal, and every tool call is logged so the final answer can show
the exact path behind it.
"""

from __future__ import annotations

from .db import connect

# Tool registry: name -> {"description": ..., "params": [...], "query": cypher}
# The LLM sees only the name/description/params — not the Cypher, which it
# shouldn't need to (it can, though: the query plan is shown in the UI).

TOOLS: dict[str, dict] = {}


def tool(name: str, description: str, params: list[str]):
    def deco(fn):
        TOOLS[name] = {
            "description": description,
            "params": params,     # ordered, positional
            "fn": fn,
        }
        return fn
    return deco


def _rows(res) -> list[dict]:
    """FalkorDB header rows are (col_type, name) tuples -> dicts."""
    names = [h[1] for h in res.header]
    return [dict(zip(names, r)) for r in res.result_set]


# open alerts --------------------------------------------------------------
@tool(
    "get_open_alerts",
    "List currently open fraud alerts with amount, source/destination accounts, "
    "and the reasons they were flagged.",
    [],
)
def get_open_alerts(g):
    res = g.query(
        "MATCH (al:Alert {status:'open'})-[:ON]->(a:Account) "
        "RETURN al.id AS alert, al.txnId AS txn, al.amount AS amount, "
        "al.reasons AS reasons, a.id AS src "
    )
    return [r for r in res.result_set]


@tool(
    "get_alert",
    "Full details of a single alert by its ID (e.g. AL-0001): what transaction "
    "triggered it, amount, and who sent it.",
    ["alert_id"],
)
def get_alert(g, alert_id):
    res = g.query(
        "MATCH (al:Alert {id:$id})-[:ON]->(a:Account) "
        "OPTIONAL MATCH (a)-[t:TRANSFERRED {id: al.txnId}]->(b:Account) "
        "RETURN al.id AS alert_id, al.txnId AS txn_id, al.amount AS flagged_amount, "
    "al.reasons AS reasons, a.id AS src_id, a.name AS src_name, a.openedDaysAgo AS src_account_age_days, "
        "a.country AS src_country, b.id AS dst_id, b.name AS dst_name, "
        "b.openedDaysAgo AS dst_account_age_days, t.amount AS transfer_amount",
        {"id": alert_id},
    )
    if not res.result_set:
        return {"error": f"no alert {alert_id}"}
    return _rows(res)[0]


@tool(
    "account_profile",
    "Profile of one account: holder name, country, tier, age in days, flagged status, "
    "total transfers sent and received, total paid out.",
    ["account_id"],
)
def account_profile(g, account_id):
    res = g.query(
        "MATCH (a:Account {id:$id}) "
        "OPTIONAL MATCH (a)-[t:TRANSFERRED]->(x) "
        "OPTIONAL MATCH (y)-[t2:TRANSFERRED]->(a) "
        "RETURN a.id AS id, a.name AS name, a.country AS country, a.tier AS tier, "
        "a.openedDaysAgo AS age_days, a.flagged AS flagged, "
        "count(DISTINCT t) AS transfers_sent, count(DISTINCT t2) AS transfers_received, "
        "coalesce(sum(t.amount), 0) AS total_sent",
        {"id": account_id},
    )
    if not res.result_set:
        return {"error": f"no account {account_id}"}
    return _rows(res)[0]


@tool(
    "account_connections",
    "Everything ONE hop from an account: its devices, login IPs, cards, "
    "merchants it paid, and direct transfer counterparties.",
    ["account_id"],
)
def account_connections(g, account_id):
    out: dict[str, list] = {"devices": [], "ips": [], "cards": [], "paid_to": [], "transfers_out": [], "transfers_in": []}
    r = g.query(
        "MATCH (a:Account {id:$id})-[:USES_DEVICE]->(d:Device) RETURN collect(DISTINCT d.id) AS ids", {"id": account_id})
    out["devices"] = r.result_set[0][0] if r.result_set else []
    r = g.query(
        "MATCH (a:Account {id:$id})-[:LOGGED_FROM]->(i:Ip) RETURN collect(DISTINCT i.id) AS ids", {"id": account_id})
    out["ips"] = r.result_set[0][0] if r.result_set else []
    r = g.query(
        "MATCH (a:Account {id:$id})-[:HAS_CARD]->(c:Card) RETURN collect(DISTINCT c.id) AS ids", {"id": account_id})
    out["cards"] = r.result_set[0][0] if r.result_set else []
    r = g.query(
        "MATCH (a:Account {id:$id})-[p:PAID]->(m:Merchant) "
        "RETURN collect({merchant:m.id, name:m.name, category:m.category, amount:p.amount}) AS paid", {"id": account_id})
    out["paid_to"] = r.result_set[0][0] if r.result_set else []
    r = g.query(
        "MATCH (a:Account {id:$id})-[t:TRANSFERRED]->(b:Account) "
        "RETURN collect({txn:t.id, to:b.id, to_name:b.name, amount:t.amount, age_days:b.openedDaysAgo}) AS out", {"id": account_id})
    out["transfers_out"] = r.result_set[0][0] if r.result_set else []
    r = g.query(
        "MATCH (a2:Account)-[t:TRANSFERRED]->(a:Account {id:$id}) "
        "RETURN collect({txn:t.id, from:a2.id, from_name:a2.name, amount:t.amount, age_days:a2.openedDaysAgo}) AS inn", {"id": account_id})
    out["transfers_in"] = r.result_set[0][0] if r.result_set else []
    return out


@tool(
    "shared_endpoints",
    "Which OTHER accounts share a device, IP, or card with the given account — "
    "the core fraud-ring signal. Returns endpoint id + sharers.",
    ["account_id"],
)
def shared_endpoints(g, account_id):
    res = g.query(
        "MATCH (a:Account {id:$id})-[:USES_DEVICE|LOGGED_FROM|HAS_CARD]->(ep) "
        "<-[:USES_DEVICE|LOGGED_FROM|HAS_CARD]-(b:Account) "
        "WHERE b.id <> a.id "
        "RETURN ep.id AS endpoint, labels(ep)[0] AS endpoint_type, "
        "collect(DISTINCT {id: b.id, name: b.name, age_days: b.openedDaysAgo, flagged: b.flagged}) AS sharers",
        {"id": account_id},
    )
    return [dict(zip(("endpoint", "endpoint_type", "sharers"), r)) for r in res.result_set]


@tool(
    "trace_money_path",
    "Follow the money: all account-to-account transfer paths starting at an account, "
    "up to N hops. Shows who eventually receives the money (and where it cashes out).",
    ["account_id", "max_hops"],
)
def trace_money_path(g, account_id, max_hops):
    hops = int(max_hops)
    res = g.query(
        f"MATCH path = (a:Account {{id:$id}})-[:TRANSFERRED*1..{hops}]->(b:Account) "
        "RETURN [n IN nodes(path) | n.id] AS accounts, "
        "[x IN relationships(path) | x.amount] AS amounts, "
        "[x IN relationships(path) | x.id] AS txns, "
        "length(path) AS hops",
        {"id": account_id},
    )
    return _rows(res) if res.result_set else []


@tool(
    "shortest_path",
    "Shortest DIRECTED connection path between two accounts through any relationship type — "
    "follows how money/value flowed from one account to the other. "
    "Finds the cheapest evidence trail linking them.",
    ["from_account", "to_account"],
)
def shortest_path(g, from_account, to_account):
    res = g.query(
        "MATCH (a:Account {id:$src}), (b:Account {id:$dst}) "
        "WITH a, b, shortestPath((a)-[*1..5]->(b)) AS p "
        "RETURN [n IN nodes(p) | coalesce(n.name, n.id)] AS hops, "
        "[r IN relationships(p) | type(r)] AS via",
        {"src": from_account, "dst": to_account},
    )
    return _rows(res) if res.result_set else []


@tool(
    "ring_extent",
    "Find the suspected connected group around an account: all accounts reachable "
    "through devices shared by flagged accounts. Reveals the size of the cluster.",
    ["account_id"],
)
def ring_extent(g, account_id):
    res = g.query(
        "MATCH (a:Account {id:$id})-[ed1:USES_DEVICE]->(d:Device)<-[ed2:USES_DEVICE]-(b:Account) "
        "RETURN collect(DISTINCT a.id) AS probe, count(DISTINCT b) AS peer_accounts, "
        "collect(DISTINCT b.id) AS peers", {"id": account_id})
    return _rows(res) if res.result_set else []


@tool(
    "close_alert",
    "WRITE: mark an alert as closed. Params: alert id, action "
    "('block' | 'watch' | 'clear'), one-line justification. "
    "Call this once, at the end, with your verdict.",
    ["alert_id", "action", "justification"],
)
def close_alert(g, alert_id, action, justification):
    if action not in ("block", "watch", "clear"):
        return {"error": f"invalid action {action}"}
    g.query(
        "MATCH (al:Alert {id:$id}) SET al.status='closed', al.action=$action, "
        "al.actionedBy='casefile-agent', al.justification=$why RETURN al.id",
        {"id": alert_id, "action": action, "why": justification},
    )
    return {"ok": True, "alert": alert_id, "status": "closed", "action": action}


def run_tool(g, name: str, args: list) -> object:
    spec = TOOLS.get(name)
    if spec is None:
        return {"error": f"unknown tool {name}"}
    try:
        return spec["fn"](g, *args)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
