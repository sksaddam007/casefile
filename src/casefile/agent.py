"""The CaseFile agent: an LLM with graph tools — nothing else.

No vector store, no RAG pile of text. Every fact the agent knows comes
from a Cypher traversal the agent chose to run. The full trail
(thought -> tool -> query -> result) is kept and rendered, so every
verdict can be traced back through the graph.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.rule import Rule

from .db import connect
from .llm import get_client, get_model
from .tools import TOOLS, run_tool

SYSTEM_PROMPT = """\
You are CaseFile, a fraud analyst working for a bank's financial crime team.

You have tools backed by the bank's relationship graph in FalkorDB. Accounts,
devices, IP addresses, cards, merchants and transfers are nodes and edges.
Fraud rings manifest as shared endpoints: multiple accounts behind one device,
one IP, or one card, and chains of transfers to fresh accounts cashing out.

Method (follow it):
1. Read the alert facts.
2. PROFILE the source account, then its CONNECTIONS.
3. Before ANY verdict, look for shared infrastructure (shared_endpoints) and
   follow the money (trace_money_path) at least 2 hops.
4. Weigh innocent sharing too: 2 accounts on one shared family device is
   ordinary life; 6 young accounts rotating between 2 devices is a ring. Use
   account age, flagged status, and money flow to tell one from the other.
5. Choose block / watch / clear. "watch" is for accumulation of strong
   circumstantial evidence awaiting one hard confirmation. "close_alert" once.
6. Your final answer must: state the verdict, then walk the evidence hop by
   hop (who shared what device/IP, where the money went, how it cashed out),
   and note the innocent sharers you ruled out and WHY you ruled them out.

Rules:
- Every fact must come from a tool result. Never invent names, ids, or amounts.
- Keep total tool calls under 8. Prefer deciding from evidence you already have.
"""


@dataclass
class TrailEntry:
    thought: str
    tool: str
    args: list
    result: object
    ms: int
    sql_hint: str = ""


@dataclass
class Trail:
    entries: list[TrailEntry] = field(default_factory=list)
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0

    def summary(self) -> dict:
        return {
            "tool_calls": len(self.entries),
            "query_ms_total": sum(e.ms for e in self.entries),
            "llm_prompt_tokens": self.llm_prompt_tokens,
            "llm_completion_tokens": self.llm_completion_tokens,
        }


def _openai_tools_schema() -> list[dict]:
    """Translate tool registry -> OpenAI function-calling schema."""
    schemas = []
    for name, spec in TOOLS.items():
        props, required = {}, []
        for i, p in enumerate(spec["params"]):
            t = "integer" if p.endswith("hops") else "string"
            props[p] = {"type": t, "description": f"param {i+1}: {p}"}
            required.append(p)
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": spec["description"],
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        })
    return schemas


class CaseFileAgent:
    def __init__(self, console: Console | None = None, quiet: bool = False):
        self.g = connect()
        self.client = get_client()
        self.model = get_model()
        self.console = console or Console()
        self.quiet = quiet
        self.trail = Trail()

    # -- UI -------------------------------------------------------------
    def _say(self, *args, **kwargs):
        if not self.quiet:
            self.console.print(*args, **kwargs)

    # -- loop -----------------------------------------------------------
    def investigate(self, question: str, alert_id: str | None = None) -> str:
        """Run the agent. Returns its final answer (the verdict)."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        best_answer = ""          # richest assistant text seen so far
        forced = False
        for _ in range(12):
            # after the evidence budget, stop offering tools -> forced verdict
            tools_schema = _openai_tools_schema() if len(self.trail.entries) < 8 else None
            if tools_schema is None and not forced:
                forced = True
                messages.append({
                    "role": "system",
                    "content": "Tool budget exhausted. You have enough evidence. "
                               "Produce the final verdict answer NOW. No more tool calls.",
                })
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools_schema,
                    temperature=0.2,
                )
            except Exception as e:
                self._say(
                    Panel(
                        f"[red]{type(e).__name__}:[/red] {str(e)[:300]}\n\n"
                        "[yellow]Check your LLM settings in .env:[/yellow]\n"
                        "  OPENAI_API_KEY  (start with a FULL key from your provider)\n"
                        "  OPENAI_BASE_URL (provider's OpenAI-compatible endpoint)\n"
                        "  OPENAI_MODEL    (a model the provider serves)\n\n"
                        "Offline deterministic demo: CASEFILE_MOCK=1 ./demo.sh",
                        title="LLM call failed", border_style="red"))
                raise
            msg = resp.choices[0].message
            self.trail.llm_prompt_tokens += resp.usage.prompt_tokens
            self.trail.llm_completion_tokens += resp.usage.completion_tokens

            tool_calls = msg.tool_calls or []
            # keep the richest text the model produced (some models narrate
            # before the final tool call, then return '' at the very end)
            content_text = (msg.content or "").strip()
            if content_text and len(content_text) > len(best_answer):
                best_answer = content_text
            if content_text:
                self._say(content_text, style="dim")

            if not tool_calls:
                return content_text or best_answer or "(no answer produced)"

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in tool_calls],
            })

            for tc in tool_calls:
                name = tc.function.name
                try:
                    argv = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    argv = {}
                args_list = list(argv.values()) if isinstance(argv, dict) else []
                t0 = time.perf_counter()
                result = run_tool(self.g, name, args_list)
                ms = int((time.perf_counter() - t0) * 1000)
                self.trail.entries.append(TrailEntry(
                    thought=tc.id, tool=name, args=args_list,
                    result=result, ms=ms,
                ))
                self._render_step(name, args_list, result, ms)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str)[:4000],
                })
        return "(stopped: step limit)"

    def _render_step(self, name, args, result, ms):
        argstr = ", ".join(str(a) for a in args)
        result_show = json.dumps(result, default=str)
        if len(result_show) > 300:
            result_show = result_show[:300] + "…"
        self._say(
            Panel(
                f"[bold blue]{name}[/bold blue]({argstr})   "
                f"[dim]falkordb · {ms} ms[/dim]\n{result_show}",
                border_style="blue",
                subtitle="graph tool",
                subtitle_align="left",
            )
        )


def save_trail(agent: CaseFileAgent, alert_id: str) -> str:
    """Dump the full evidence trail (every tool call + raw result) to disk."""
    import pathlib
    import time
    out_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "evidence"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"{alert_id or 'session'}-{int(time.time())}.json"
    payload = {
        "trail": [
            {"tool": e.tool, "args": e.args,
             "result": json.loads(json.dumps(e.result, default=str)),
             "ms": e.ms}
            for e in agent.trail.entries
        ],
        "summary": agent.trail.summary(),
    }
    path.write_text(json.dumps(payload, indent=2))
    return str(path)


def run_single(alert_id: str) -> str:
    console = Console()
    agent = CaseFileAgent(console=console)
    q = (
        f"Investigate fraud alert {alert_id} from the bank's graph and decide: "
        "block, watch, or clear. Cite the evidence path for your decision, "
        "then close the alert with your verdict."
    )
    console.rule(f"[bold red]CaseFile — investigating {alert_id}")
    answer = agent.investigate(q, alert_id)
    console.rule("[bold green]VERDICT")
    console.print(Panel(answer, border_style="green"))
    console.print(f"[dim]{agent.trail.summary()}[/dim]")
    console.print(f"[dim]evidence trail saved: {save_trail(agent, alert_id)}[/dim]")
    return answer


if __name__ == "__main__":
    import sys
    run_single(sys.argv[1] if len(sys.argv) > 1 else "AL-0001")
