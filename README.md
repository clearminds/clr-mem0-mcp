# clr-mem0-mcp

MCP server for the self-hosted [mem0](https://github.com/mem0ai/mem0) memory API
(the upstream `server/` stack: REST API with `X-API-Key` auth, pgvector, LLM-based fact extraction).
Gives Claude (Code, Desktop, web) and other MCP clients the same long-term memory Hermes and Open WebUI use.

Tools: `mem0_search`, `mem0_list`, `mem0_get`, `mem0_history` (read); `mem0_add`, `mem0_update` (write);
`mem0_delete` (destructive). See [skills/mem0/SKILL.md](skills/mem0/SKILL.md).

## Hosted

`https://mem0.mcp.example.com/mcp` — a per-service stack behind an OIDC auth proxy
in front via mcp-auth-proxy. The stack's `MEM0_API_KEY` is a per-user key from the mem0 dashboard and
`MEM0_USER_ID` the default memory owner.

## Local (stdio)

```bash
export MEM0_URL=https://mem0-api.example.com
export MEM0_API_KEY=m0sk_...      # dashboard -> API Keys
export MEM0_USER_ID=alice
uvx --from git+ssh://git@github.com/clearminds/clr-mem0-mcp.git clr-mem0-mcp
```

or `~/.config/mem0/credentials.json` with `url`, `api_key`, `user_id`. `--read-only` hides the write tools.

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

Image: `ghcr.io/clearminds/clr-mem0-mcp:latest`, built by `.github/workflows/docker.yml` on push to main.
