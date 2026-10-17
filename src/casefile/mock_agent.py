"""Deterministic scripted agent for CI / offline demo.

Suspends the LLM and replays the exact investigation an expert analyst
would run, using the same tool registry. Lets us demo and test the full
loop (tool calls -> graph -> verdict write-back) with zero network.

Enable: CASEFILE_MOCK=1 (or CASEFILE_MOCK=true)
"""

from __future__ import annotations

import json

from .agent import CaseFileAgent, TrailEntry
from .tools import run_tool

SCRIPT = [
    ("get_alert", ["AL-0001"]),
    ("account_profile", ["FR-04"]),
    ("account_connections", ["FR-04"]),
    ("shared_endpoints", ["FR-04"]),
    ("trace_money_path", ["FR-04", 3]),
    ("account_profile", ["FR-03"]),
    ("close_alert", ["AL-0001", "block",
                     "Six young accounts share two devices and one IP; "
                     "funds from FR-04 chain through FR-02 to FR-03 and "
                     "cash out via SpeedXChange merchant — laundering ring."]),
]


class MockAgent(CaseFileAgent):
    """Same UI/trail as the real agent; LLM replaced by the script."""

    def __init__(self, console=None, quiet: bool = False):
        super().__init__(console=console, quiet=quiet)
        self._script_weapon = 0

    def investigate(self, question: str, alert_id: str | None = None) -> str:
        for i, (name, args) in enumerate(SCRIPT, 1):
            import time
            t0 = time.perf_counter()
            result = run_tool(self.g, name, args)
            ms = int((time.perf_counter() - t0) * 1000)
            self.trail.entries.append(TrailEntry(
                thought=f"script step {i}", tool=name, args=args,
                result=result, ms=ms))
            self._render_step(name, args, result, ms)

        return (
            "**VERDICT: BLOCK** — laundering ring of six young accounts.\n\n"
            "Evidence path:\n"
            "1. Alert AL-0001: $8,150.50 transfer FR-04 (Sofia Novak, 69-day account) → FR-02.\n"
            "2. Shared endpoints: FR-04 shares device DEV-fr-a with FR-01, FR-02, FR-03, FR-05, "
            "FR-06 — all flagged, all 18–83 days old — and rotates IP-fr-1/IP-fr-2.\n"
            "3. Only ONE innocent account (Olivia Silva, DEV-fr-a, 66 years old) shares any device — "
            "ruled out: she has ten months of normal payment history.\n"
            "4. Money path: FR-04 → FR-02 ($7,900 onward) → FR-05 → FR-03, cash-out "
            "payments from ring members to SpeedXChange merchant.\n"
            "5. Pattern = classic mule chain via shared stolen devices. "
            "Alert closed as 'block'; recommend freezing all six accounts and reviewing the "
            "innocent sharer for possible identity theft."
        )


def main():
    from rich.console import Console
    from .agent import save_trail

    console = Console()
    agent = MockAgent(console=console)
    console.rule("[bold red]CaseFile (mock) — investigating AL-0001")
    answer = agent.investigate("Investigate fraud alert AL-0001.")
    console.rule("[bold green]VERDICT")
    console.print(answer)
    print("TRAIL SUMMARY:", json.dumps(agent.trail.summary()))
    print("EVIDENCE TRAIL:", save_trail(agent, "AL-0001"))


if __name__ == "__main__":
    main()
