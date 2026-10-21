"""mem0 MCP Server — FastMCP tools for the self-hosted mem0 memory API (the upstream server/ REST API)."""

import argparse
import logging
import sys
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from clr_mem0_mcp.config import Settings
from clr_mem0_mcp.middleware import ToolValidationMiddleware

mcp = FastMCP("mem0")
mcp.add_middleware(ToolValidationMiddleware())
_settings: Settings | None = None
_client: httpx.Client | None = None

# Imported here (not at the top) on purpose: annotations.py needs ``mcp`` from
# this module, so importing it before the ``mcp = FastMCP(...)`` line above
# would be a circular import. Do not move.
from clr_mem0_mcp.annotations import (  # noqa: E402
    destructive_tool,
    read_tool,
    remove_non_read_tools,
    write_tool,
)

# ── HTTP plumbing ────────────────────────────────────────────────────


def _api() -> httpx.Client:
    if _client is None:
        raise ToolError("mem0 MCP is not configured (missing MEM0_URL / MEM0_API_KEY).")
    return _client


def _request(method: str, path: str, **kwargs: Any) -> Any:
    """Call the mem0 REST API; turn HTTP errors into readable tool errors."""
    try:
        resp = _api().request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise ToolError(f"mem0 API unreachable: {exc}") from exc
    if resp.status_code >= 400:
        detail: Any
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        raise ToolError(f"mem0 API {resp.status_code} on {method} {path}: {detail}")
    if not resp.content:
        return {}
    return resp.json()


def _scope(user_id: str | None, agent_id: str | None, run_id: str | None) -> dict[str, str]:
    """Who the memory belongs to. Defaults to the configured user when nothing is given."""
    scope = {
        k: v
        for k, v in {"user_id": user_id, "agent_id": agent_id, "run_id": run_id}.items()
        if v
    }
    if not scope:
        scope["user_id"] = _settings.mem0_user_id if _settings else ""
    if not any(scope.values()):
        raise ToolError("No user_id/agent_id/run_id given and MEM0_USER_ID is not configured.")
    return scope


# ── Tools ────────────────────────────────────────────────────────────


@read_tool
def mem0_search(
    query: str,
    user_id: str | None = None,
    agent_id: str | None = None,
    run_id: str | None = None,
    top_k: int = 10,
    threshold: float | None = None,
) -> dict[str, Any]:
    """Search memories semantically (the normal way to recall what is known about someone/something).

    Args:
        query: Natural-language question or topic, e.g. "how does Alice take her coffee".
        user_id: Whose memories to search; defaults to the configured user.
        agent_id: Optional agent scope (memories an agent stored for itself).
        run_id: Optional session/run scope.
        top_k: Maximum number of hits (default 10).
        threshold: Minimum similarity score 0..1; omit to let mem0 decide.

    Returns:
        {"results": [{"id", "memory", "score", "user_id", "metadata", "created_at", ...}]}
    """
    body: dict[str, Any] = {"query": query, "filters": _scope(user_id, agent_id, run_id), "top_k": top_k}
    if threshold is not None:
        body["threshold"] = threshold
    return _request("POST", "/search", json=body)


@read_tool
def mem0_list(
    user_id: str | None = None,
    agent_id: str | None = None,
    run_id: str | None = None,
    top_k: int = 100,
) -> dict[str, Any]:
    """List all memories for a user/agent/run (no ranking; use mem0_search for a question).

    Args:
        user_id: Whose memories; defaults to the configured user.
        agent_id: Optional agent scope.
        run_id: Optional session/run scope.
        top_k: Maximum number of memories to return (default 100, max 1000).

    Returns:
        {"results": [{"id", "memory", "metadata", "created_at", "updated_at", ...}]}
    """
    params = {**_scope(user_id, agent_id, run_id), "top_k": top_k}
    return _request("GET", "/memories", params=params)


@read_tool
def mem0_get(memory_id: str) -> dict[str, Any]:
    """Get one memory by id.

    Args:
        memory_id: The memory's UUID (from mem0_search / mem0_list).
    """
    return _request("GET", f"/memories/{memory_id}")


@read_tool
def mem0_history(memory_id: str) -> Any:
    """Show how a memory changed over time (ADD / UPDATE / DELETE events).

    Args:
        memory_id: The memory's UUID.
    """
    return _request("GET", f"/memories/{memory_id}/history")


@write_tool
def mem0_add(
    text: str,
    user_id: str | None = None,
    agent_id: str | None = None,
    run_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    infer: bool = True,
) -> dict[str, Any]:
    """Remember something. mem0 extracts the facts with an LLM and merges them with what it already knows
    (ADD / UPDATE / DELETE / NONE per fact), so pass what was said or learned, not a pre-digested list.

    Args:
        text: What to remember, e.g. "Alice drinks her coffee without milk" or a chat turn worth keeping.
        user_id: Whose memory this is; defaults to the configured user.
        agent_id: Set when an agent stores something about itself/its task rather than about the user.
        run_id: Optional session/run scope for short-lived context.
        metadata: Free-form tags, e.g. {"source": "claude-code", "project": "clearai"}.
        infer: True (default) = extract facts with the LLM; False = store the text verbatim as one memory.

    Returns:
        {"results": [{"id", "memory", "event": "ADD|UPDATE|DELETE|NONE"}]} -- an empty list means nothing new.
    """
    body: dict[str, Any] = {
        "messages": [{"role": "user", "content": text}],
        **_scope(user_id, agent_id, run_id),
        "infer": infer,
    }
    if metadata:
        body["metadata"] = metadata
    return _request("POST", "/memories", json=body, timeout=600)


@write_tool
def mem0_update(memory_id: str, text: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Rewrite one memory's text (and optionally its metadata) in place.

    Args:
        memory_id: The memory's UUID.
        text: The corrected memory text.
        metadata: Replacement metadata; omit to keep the current one.
    """
    body: dict[str, Any] = {"text": text}
    if metadata is not None:
        body["metadata"] = metadata
    return _request("PUT", f"/memories/{memory_id}", json=body)


@destructive_tool
def mem0_delete(memory_id: str) -> dict[str, Any]:
    """Delete one memory permanently.

    Args:
        memory_id: The memory's UUID.
    """
    return _request("DELETE", f"/memories/{memory_id}")


# ── Entry point ──────────────────────────────────────────────────────


def main() -> None:
    """Start the MCP server."""
    global _settings, _client

    parser = argparse.ArgumentParser(description="mem0 MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="HTTP host (--transport http)")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port (--transport http)")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument(
        "--read-only", action="store_true", default=None, help="Hide the add/update/delete tools"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    _settings = Settings(mem0_transport=args.transport, mem0_log_level=args.log_level)
    creds = _settings.load_credentials()
    if not creds.get("url") or not creds.get("api_key"):
        logging.error(
            "Missing credentials: set MEM0_URL and MEM0_API_KEY (env) "
            "or create ~/.config/mem0/credentials.json"
        )
        sys.exit(1)
    _settings.mem0_user_id = creds.get("user_id", _settings.mem0_user_id)
    _client = httpx.Client(
        base_url=creds["url"].rstrip("/"),
        headers={"X-API-Key": creds["api_key"]},
        timeout=httpx.Timeout(60.0, read=600.0),
    )

    read_only = args.read_only if args.read_only is not None else _settings.mem0_read_only
    if read_only:
        removed = remove_non_read_tools(mcp)
        logging.info("Read-only mode: %d non-read tools removed", removed)

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
