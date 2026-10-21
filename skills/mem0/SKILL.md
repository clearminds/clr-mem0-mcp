---
name: mem0
description: This skill should be used when the user asks to "remember this", "what do you know about me / X", "forget that", "recall", "save to memory", mentions mem0 or long-term memory, or when something worth remembering across sessions comes up (preferences, decisions, facts about people, projects, infrastructure).
user_invocable: true
version: 0.1.0
---

# mem0 — long-term memory

Shared long-term memory for your agents (Claude, Hermes, Open WebUI, ...) in a self-hosted mem0. Memories are scoped by `user_id` (a person), optionally `agent_id`
(an agent's own notes) and `run_id` (a session). The default `user_id` comes from the configuration.

## Configuration

**Hosted:** an HTTP MCP endpoint behind your OIDC proxy — nothing to configure on the client.

**Local (stdio):** env vars, or `~/.config/mem0/credentials.json`:

```bash
mkdir -p ~/.config/mem0
cat > ~/.config/mem0/credentials.json <<'EOF'
{
  "url": "https://mem0-api.example.com",
  "api_key": "m0sk_...",
  "user_id": "alice"
}
EOF
chmod 600 ~/.config/mem0/credentials.json
```

API keys are made in the mem0 dashboard (API Keys), one per client.

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `mem0_search` | Semantic recall | `query` (required), `user_id`, `agent_id`, `run_id`, `top_k` (10), `threshold` |
| `mem0_list` | Everything stored for a scope | `user_id`, `agent_id`, `run_id`, `top_k` (100) |
| `mem0_get` | One memory | `memory_id` |
| `mem0_history` | Change log of one memory | `memory_id` |
| `mem0_add` | Remember something (LLM extracts and merges facts) | `text` (required), `user_id`, `agent_id`, `run_id`, `metadata`, `infer` (true) |
| `mem0_update` | Rewrite one memory | `memory_id`, `text`, `metadata` |
| `mem0_delete` | Delete one memory | `memory_id` |

## Workflow

| User Request | MCP Tool |
|-------------|----------|
| "What do you know about my coffee habits?" | `mem0_search(query="coffee habits")` |
| "Remember that I always deploy via CI, never local tags" | `mem0_add(text="Alice always releases via the CI pipeline, never local tags")` |
| "What have you stored about me?" | `mem0_list()` |
| "That's wrong, I drink it black" | `mem0_search(...)` then `mem0_update(memory_id, text="Alice drinks her coffee black")` |
| "Forget my old phone number" | `mem0_search(...)` then `mem0_delete(memory_id)` |

Search before adding when a correction is likely: mem0 merges on `mem0_add`, but a targeted
`mem0_update` is more precise. `mem0_add` takes a few seconds up to a minute (an LLM extracts the facts).

## Safety

**Read-only (safe):** `mem0_search`, `mem0_list`, `mem0_get`, `mem0_history`.

**Write (confirm when in doubt):** `mem0_add`, `mem0_update` — they change what every agent recalls.

**Destructive (always confirm):** `mem0_delete`.

## Notes

- Pass `agent_id` for an agent's own working notes, keep `user_id` for facts about the person.
- `infer=false` stores text verbatim (no LLM) — for exact snippets like IDs or commands.
- Scores from `mem0_search` are cosine similarities (0–1); below ~0.4 is usually noise.
