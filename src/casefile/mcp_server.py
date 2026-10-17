"""MCP server exposing CaseFile's graph tools.

Same 9 tools the CaseFile agent uses over the LLM tool-calling loop,
published over the Model Context Protocol so ANY MCP client (Claude
Desktop, Cursor, another vendor agent) can investigate the same bank
graph. This checks the hackathon brief's "tool selection through MCP"
box: the graph tools are protocol-level, not baked into one agent.

Run:  uv run python -m casefile.mcp_server
Then add to your MCP client config, e.g. Claude Desktop:
  {"mcpServers": {"casefile": {"command": "<abs>/casefile/.venv/bin/python",
   "args": ["-m", "casefile.mcp_server"], "env": {...}}}}
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from .db import HOST, PORT, GRAPH_NAME, connect
from .tools import TOOLS, run_tool

mcp = FastMCP("casefile-fraud-graph")

# spin up one shared graph connection at import
_GRAPH = connect()


def _mcp_tool(name: str):
    """Build a plain function exposing one casefile tool as MCP tool."""
    spec = TOOLS[name]
    params = spec["params"]

    def _fn(**kwargs):
        args = [kwargs[p] for p in params]
        return json.dumps(run_tool(_GRAPH, name, args), default=str)

    return _fn


for tname, spec in TOOLS.items():
    fn = _mcp_tool(tname)
    params = spec["params"]
    doc_txt = (f"{spec['description']}  [params: {', '.join(params) or 'none'}]")
    fn.__name__ = tname
    fn.__doc__ = doc_txt
    mcp.tool(name=tname, description=doc_txt)(fn)


@mcp.tool(name="graph_info", description="Which FalkorDB host/graph this server is wired to.")
def graph_info():
    import socket
    return {"host": HOST, "port": PORT, "graph": GRAPH_NAME}


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
