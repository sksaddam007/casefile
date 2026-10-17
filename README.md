# CaseFile — a fraud analyst agent that walks the graph

**Graph Hacks hackathon entry (WeMakeDevs × FalkorDB) — Track 01: Agents That Act on Connected Data.**

CaseFile is a financial-crime investigation agent. When a transfer gets flagged, the agent doesn't
stare at a pile of text — it *traverses a graph*: follows the money across accounts, finds hidden
shared devices and IPs behind seemingly unrelated customers, weighs innocent sharing against
fraud-ring signals, decides **block / watch / clear**, and closes the alert with every fact it used
traceable back to a Cypher query.

No vector-store RAG. No prompt-stuffed context. Every fact is a traversal the agent chose to run.

## 🎬 Demo video

Watch the full investigation here → [casefile_demo.mp4](https://github.com/sksaddam007/casefile/raw/main/casefile_demo.mp4) (2 min, narrated)
*same labeled verdict gets produced live by `./demo.sh` (or `./present.sh` for the timed version).*

## The 40-second story

1. An alert fires: **$8,150.50 FR-04 → FR-02**, both accounts weeks old. Ordinary? Could be.
2. The agent runs `shared_endpoints`: **six young accounts** rotate between exactly **two devices**
   and one login IP — a laundering ring no single-customer view could ever reveal.
   Also on those devices: *one innocent 20-year-old customer* (decoy). The agent rules her out —
   her account has months of normal payment history.
3. `trace_money_path`: FR-04 → FR-02 → FR-05 → FR-03, cash-out payments to one merchant.
4. Verdict **block**, written back to the graph with the justification. Replay the whole trail.

## Architecture

```
                 ┌───────────────────────────────┐
 question ─────► │  CaseFile agent (tool loop)   │
                 │  OpenAI-compatible LLM        │
                 └──────┬────────────────────────┘
                        │ picks from 9 graph tools
                        ▼
                 ┌───────────────────────────────┐      also exposed as an MCP server
                 │ FalkorDB (relationship graph) │◄──── so ANY MCP client can use the
                 │  accounts·devices·IPs·cards   │      same 9 tools over the protocol
                 │  transfers·merchants·alerts   │
                 └───────────────────────────────┘
```

- **`casefile/tools.py`** — 9 graph tools (Cypher traversals): alerts, profiles, 1-hop
  connections, shared-endpoint detection, fixed-length money paths, `shortestPath`, cluster
  extent, and `close_alert` (the agent's write action).
- **`casefile/agent.py`** — provider-agnostic tool-calling loop. Every call and result is kept in
  an evidence trail; the final verdict prints it. `CASEFILE_MOCK=1` runs a scripted
  deterministic investigation (CI / offline demo).
- **`casefile/mcp_server.py`** — the same 9 tools published over the
  [Model Context Protocol](https://modelcontextprotocol.io), so Claude Desktop / Cursor / any MCP
  client gets native fraud-investigation tools. Run with `uv run python -m casefile.mcp_server`.
- **`casefile/generator.py` + `loader.py`** — deterministic synthetic bank graph (~400 accounts)
  with a **planted 6-account fraud ring**, loaded via `UNWIND` batches in seconds.

## Run it

```bash
# 1. FalkorDB (Redis protocol) + its visual Browser
docker run -d --name casefile-falkordb -p 6380:6379 falkordb/falkordb:latest
docker run -d --name casefile-browser  -p 3100:3000 --link casefile-falkordb:falkordb falkordb/falkordb-browser:latest
#   Browser UI: http://localhost:3100

# 2. Python env + deps + LLM settings (any OpenAI-compatible endpoint)
uv venv && uv pip install -e . && cp .env.example .env
#   we test with a LOCAL Ollama model - zero cloud dependency:
#   OPENAI_API_KEY=ollama / OPENAI_BASE_URL=http://127.0.0.1:11434/v1
#   OPENAI_MODEL=qwen3.5-64k:latest

# 3. One command: fresh graph + full demo investigation
./demo.sh                     # real LLM
CASEFILE_MOCK=1 ./demo.sh     # scripted, offline (no LLM needed)
```

Show the fraud ring in the Browser:

```cypher
MATCH (a:Account {id:'FR-04'})-[t:TRANSFERRED*1..3]-(b:Account) RETURN a, b
```

## Why a graph (the one-paragraph answer)

"Which accounts are linked to this flagged transfer?" is a question **about relationships**, not
records. In SQL that's N joins and no N. In CaseFile it's one Cypher hop:
`MATCH (a:Account)-[:USES_DEVICE]->(d)<-[:USES_DEVICE]-(b)` — instantly, on every step of the
agent loop, plus `shortestPath` and variable-length traversals as first-class tools. The graph
isn't a sidecar — it **is** the agent's working memory.

## Verified multi-hop results (from this repo's current demo data)

| Tool call | Graph answer |
|---|---|
| `shared_endpoints("FR-04")` | 6 flagged accounts share `DEV-fr-a`/`DEV-fr-b`/`IP-fr-1` + 1 innocent decoy |
| `trace_money_path("FR-04", 3)` | `FR-04 → FR-02 → FR-05 → FR-03` ($8,150.50 → $7,900 → $7,350 …) |
| `shortest_path("FR-02", "FR-03")` | 2 hops via `TRANSFERRED` |
| `close_alert(...)` | alert closed in-graph with agent's justification |

📖 [**Read the blog post: Your fraud analyst sees rows. Fraud is a shape.**](https://dev.to/sk_saddam_5cfd61d6612b97/your-fraud-analyst-sees-rows-fraud-is-a-shape-51o8)

## Team

Hackathon solo build — with GLM-5 (Z.ai) as implementation copilot.
