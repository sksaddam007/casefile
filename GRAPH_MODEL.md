# CaseFile graph data model & the Cypher the product depends on

This is exactly what the demo runs on: one FalkorDB graph (`bank`), 11 node/edge
labels, 9 agent tools, every tool = one parameterized Cypher query.

## Graph data model

```
(:Account {id, name, country, tier, openedDaysAgo, flagged})
(:Device  {id, os})
(:Ip      {id, geo})
(:Card    {id, brand})
(:Merchant{id, name, category})
(:Alert   {id, txnId, amount, ts, status, reasons, action, justification, actionedBy})

(:Account)-[:USES_DEVICE]->(:Device)
(:Account)-[:LOGGED_FROM]->(:Ip)
(:Account)-[:HAS_CARD]->(:Card)
(:Account)-[:PAID {amount, ts, flagged}]->(:Merchant)
(:Account)-[:TRANSFERRED {id, amount, ts, flagged}]->(:Account)
(:Alert)-[:ON]->(:Account)            # alert attached to the flagged account
```

Demo dataset (deterministic, seed=42): ~400 innocent accounts (1–2 devices each,
normal 1–2 login IPs, 2–6 merchant payments), one planted **6-account laundering
ring** (`FR-01…FR-06`) sharing **2 devices + 1 IP** with a 3-hop money chain
ending at a cash-out merchant, and **1 open alert** (`AL-0001` on transfer
XFER-1002). Each ring device deliberately also touches *one innocent decoy*
account, so the agent must reason per-hop instead of flagging every sharer.

## The 9 agent tools = the Cypher (src/casefile/tools.py)

| Tool (agent picks these) | What it returns | Cypher core |
|---|---|---|
| `get_open_alerts` / `get_alert` | the case paperwork | `MATCH (al:Alert {id:$id})-[:ON]->(a:Account) OPTIONAL MATCH (a)-[t:TRANSFERRED {id: al.txnId}]->(b) RETURN …` |
| `account_profile` | holder, age, totals | `MATCH (a:Account {id:$id}) OPTIONAL MATCH (a)-[t:TRANSFERRED]->(x) OPTIONAL MATCH (y)-[t2:TRANSFERRED]->(a) RETURN count(DISTINCT t), sum(t.amount) …` |
| `account_connections` | full 1-hop neighborhood | six `collect(DISTINCT …)` traversals (devices, IPs, cards, merchants, in/out transfers) |
| `shared_endpoints` | **the fraud-ring signal: everyone behind the suspect's device/IP/card** | `MATCH (a:Account {id:$id})-[:USES_DEVICE|LOGGED_FROM|HAS_CARD]->(ep)<-[:USES_DEVICE|LOGGED_FROM|HAS_CARD]-(b:Account) WHERE b.id <> a.id RETURN ep, collect(DISTINCT b)` |
| `trace_money_path` | **multi-hop money flow up to N hops** | `MATCH path = (a:Account {id:$id})-[:TRANSFERRED*1..$hops]->(b:Account) RETURN [n IN nodes(path) | n.id], [x IN relationships(path) | x.amount]` |
| `shortest_path` | **shortestPath** between two accounts | `MATCH (a:Account {id:$src}), (b:Account {id:$dst}) WITH a, b, shortestPath((a)-[*1..5]->(b)) AS p RETURN [n IN nodes(p)], [r IN relationships(p) | type(r)]` |
| `ring_extent` | cluster size around an account | shared-device peer count + peers list |
| `close_alert` | **the agent's write action** — verdict into the graph | `MATCH (al:Alert {id:$id}) SET al.status='closed', al.action=$action, al.actionedBy='casefile-agent', al.justification=$why` |

## Why these are the right tools (what the brief asked for)

- **Multi-hop reasoning** — `trace_money_path` (variable-length) + `shortest_path`.
- **Graph algorithms as agent tools** — shortestPath exposed as a callable tool; the agent decides which traversal answers the question.
- **Explainability** — every fact in the verdict maps 1:1 to a tool call; the full call→query→result trail ships as JSON (`evidence/`), and the verdict itself is *written back* into the graph (auditable state for the next session).
- **Multi-hop pattern** — the demo run: profile → connections → `shared_endpoints` (6 young accounts behind 2 devices + 1 IP, one innocent decoy ruled out) → `trace_money_path` 3 hops → `shortest_path` → `close_alert('block')`.
