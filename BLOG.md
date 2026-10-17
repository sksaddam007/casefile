# Your fraud analyst sees rows. Fraud is a shape.

*How we built CaseFile, a graph-walking investigation agent, in one hackathon day — and what it taught us about context for AI agents.*

---

An alert lands on your fraud team's queue: **$8,150.50, account FR-04 → FR-02, both customers are new.** Your analyst opens FR-04's file. Name, country, account age, recent activity. Ordinary.

Then they open FR-02's file. Also ordinary.

The products told them all of this in two separate windows — and **both windows lied by omission**, because the fraud isn't in either record. It lives *between* them:

> Five other "customers" — all weeks old — log into their accounts from **the same two phones** as FR-04. There is no customer named on those accounts that you ever met at a branch. One innocent woman shares a device with them accidentally, and she has ten months of boring grocery payments. And the money, once it lands, walks **FR-04 → FR-02 → FR-05 → FR-03** and gets paid out to the same electronics merchant.

That is a *shape*. Rows don't have shapes — **graphs do.**

## The agent that walks it

CaseFile is our hackathon agent (Graph Hacks by WeMakeDevs × FalkorDB). Its LLM has no memory of any customer in its context window. What it has instead is **nine tools, each one a Cypher traversal** over FalkorDB:

| Tool | What it hands the agent |
|---|---|
| `get_alert` / `get_open_alerts` | the paperwork: who, what, why flagged |
| `account_profile` / `account_connections` | one hop around a suspect |
| `shared_endpoints` | other accounts behind the same device / IP / card |
| `trace_money_path` | follow transfers N hops |
| `shortest_path` | cheapest evidence trail between two accounts |
| `ring_extent` | how big is the cluster around this account |
| `close_alert` | the agent's *write action* — verdict into the graph |

We deliberately gave the model **no customer data in the prompt**. It investigates by *choosing queries* and reading back results, so every fact in its final verdict is reproducible: **show the tool call, show the Cypher, you have shown the reasoning.**

The point where the demo gets applause is the decoy. The graph that incriminates six accounts also tabs one *completely innocent* woman as a device sharer. A keyword/ML-risk-score system would flag her and move on, generating a false positive (and, honestly, an unfair suspension). The agent instead runs her profile next to the other five, sees ten months of normal behavior vs. five new flag-plagued accounts, and explicitly says: *"ruled out — ordinary history, plausible shared family device."* That's reasoning over **relationships and their evidence**, not pattern-matching on a connection existing.

## Why the graph is the context layer, not a sidecar

Every serious agent question here is about connections: *which accounts are linked to this transaction, what did the money do next, who else was holding this device.* Our agent loops entirely on:

```cypher
MATCH (a:Account {id:$id})-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(b:Account)
RETURN d.id, collect(DISTINCT b.id)
```

Three hops of that — and the ring is simply *visible*. And because FalkorDB keeps the answer to `close_alert` *in the graph along with the fact pattern*, the next session starts from an evidence-labeled graph, not a blank slate. The database is the agent's memory **and** its working context.

The verdict shouldn't be a paragraph of LLM prose you have to take on faith. Ours is a trail: 7 tool calls, each one reproducible, ~10 ms of graph time total. *Agents are only as good as the context they work with* — ours works inside the shape of the problem.

---

Built with FalkorDB + Python in one day for Graph Hacks. Full code: github.com/[you]/casefile. To reproduce: `CASEFILE_MOCK=1 ./demo.sh`.
