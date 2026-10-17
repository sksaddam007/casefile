# Demo video script (~3 min, screen + voiceover)

*Record with `CASEFILE_MOCK=1 ./demo.sh` for the deterministic take, or the real-LLM take when your key works. Cut between scenes.*

---

**SCENE 1 — The problem (0:00–0:25)** — terminal, show the alert JSON
> "An alert lands: eight thousand dollars between two brand-new accounts. Every individual record looks innocent. The fraud isn't in any record — it's in the connections. Fraud is a shape, and shapes live in graphs."

**SCENE 2 — The graph (0:25–0:50)** — FalkorDB Browser, zoom out from one account
> "Same bank, one FalkorDB graph: accounts, devices, IPs, cards, transfers, merchants. One node, one hop, watch the two flagged accounts share a device with five more."

*(Preload the Browser view: `MATCH p=(a:Account {id:'FR-04'})-[*]-(b) RETURN p` … or use the ring query for a clean visual.)*

**SCENE 3 — Give the agent the task (0:50–0:35 left — 1:05 real time finish)** — run `./demo.sh`
> "All the agent gets is the alert and nine graph tools. No customer data in the prompt, no RAG dump. Everything it knows, it found by querying."

*(While the tool-call panels print: name each. "It profiles the sender... asks who shares its devices... follows the money three hops.")*

**SCENE 4 — The verdict + explainability (final 35 sec)** — final verdict panel
> "Six accounts, two devices, one IP, cash-out at SpeedXChange: BLOCK. And one innocent customer who shares a device? Ruled out, with the reason. Every line of this verdict is a tool call you can replay. The graph stored the verdict too — the next session starts from evidence, not a blank prompt."
>
> "CaseFile — agents that act on connected data. Hackathon by WeMakeDevs × FalkorDB."

## Recording tips
- Use the mock run for a clean deterministic take (always says the right thing).
- 1280×800 terminal, font ≥ 17pt, dark background.
- Record with `asciinema rec` (crisp text) or OBS; add a zoom on `shared_endpoints` panel — it's the money shot.
- Upload to YouTube unlisted *or* GitHub README GIF — submission likely links video.
