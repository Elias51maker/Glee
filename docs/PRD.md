# Glee - Multi-Agent Code Collaboration Platform

> Glee (n.): A glee club is a group of voices singing in harmony — multiple AI agents collaborating to create better code.

## Background

Coding agents are everywhere — Claude Code, Codex, Gemini CLI, Cursor, and more. They're powerful, but they all share the same problems:

1. **They work alone** — No peer review, no second opinion
2. **They have no memory** — Every session starts fresh, context is lost
3. **They're siloed** — Switching agents means starting over

## The Insight

The solution isn't another coding agent. It's an **orchestration layer** that coordinates multiple agents together.

## What is Glee?

Glee is the **orchestration hub** for AI coding agents.

```
           ┌─────────────────────────────────┐
           │             Glee                │
           │  ┌─────────┐ ┌───────────────┐ │
           │  │ Memory  │ │ Orchestration │ │
           │  └─────────┘ └───────────────┘ │
           └──────────────┬──────────────────┘
                ╱         │         ╲
         ┌──────┐    ┌──────┐    ┌──────┐
         │Claude│    │Codex │    │Gemini│
         │coder │    │review│    │frontend│
         └──────┘    └──────┘    └──────┘
```

**Key principle**: Glee connects to agents. Agents don't connect to Glee.

## User Experience

### Installation

```bash
# Install
pip install glee-cli
# or
uvx glee
```

### Basic Usage

```bash
# Start Glee
glee start

# Connect agents with roles
glee connect claude --role coder
glee connect codex --role reviewer

# Or use a config file
glee start --config glee.yaml
```

### Project Configuration

```yaml
# glee.yaml
project:
  name: my-app
  id: my-app-uuid  # Stable ID, survives renames

agents:
  - name: claude
    role: backend-coder
  - name: gemini
    role: frontend-coder
  - name: codex
    role: reviewer

memory:
  type: postgres
  url: postgresql://localhost:5432/glee

workflow:
  review:
    max_iterations: 10
    require_approval: true
```

### Workflow Example

```bash
# In Claude Code
User: Build a rate limiter

# Claude Code writes the code...
# Then Glee automatically triggers review

Glee: Sending to Codex for review...
Codex: Found 2 issues:
  1. Race condition in counter increment
  2. Missing rate limit headers in response

Glee: Issues found. Claude, please fix.

# Claude Code fixes the issues...

Glee: Re-reviewing with Codex...
Codex: LGTM ✓

Glee: Review passed after 2 iterations.
```

---

## Architecture

### Design Principle

**Glee = Universal Agent Gateway**

Glee runs locally, supports MCP and A2A protocols as input, and uses subprocess to invoke CLI agents as output.

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Agents                           │
│  ┌────────────────┐              ┌────────────────┐             │
│  │ MCP Client     │              │ A2A Client     │             │
│  │ (e.g. Claude)  │              │ (e.g. Gemini)  │             │
│  └───────┬────────┘              └───────┬────────┘             │
│          │ MCP Protocol                  │ A2A Protocol         │
└──────────┼───────────────────────────────┼──────────────────────┘
           ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                            Glee                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Protocol Layer                        │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │    │
│  │  │ MCP Server  │  │ A2A Server  │  │  REST API       │  │    │
│  │  │ (入口)       │  │ (入口)       │  │  (入口)         │  │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │                    Core Layer                            │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │    │
│  │  │Orchestrator│  │  Memory    │  │  Workflow Engine   │ │    │
│  │  └────────────┘  └────────────┘  └────────────────────┘ │    │
│  └──────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────┴──────────────────────────────┐    │
│  │                 Subprocess Manager (出口)                │    │
│  │  Invokes CLI agents with full local file access          │    │
│  └──────────────────────────┬──────────────────────────────┘    │
└─────────────────────────────┼───────────────────────────────────┘
                              │ subprocess
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
     ┌────────────┐    ┌────────────┐    ┌────────────┐
     │ Claude Code│    │   Codex    │    │  Gemini    │
     │   (CLI)    │    │   (CLI)    │    │   (CLI)    │
     └────────────┘    └────────────┘    └────────────┘
            │                 │                 │
            └─────────────────┴─────────────────┘
                              │
                     Full access to local files
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Docker                                  │
│  ┌────────────────────┐       ┌────────────────────┐            │
│  │  PostgreSQL        │       │  pgweb             │            │
│  │  (Memory Storage)  │       │  (Admin UI)        │            │
│  │  Port: 5432        │       │  Port: 8081        │            │
│  └────────────────────┘       └────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

**Protocol Gateway**:
- MCP clients (Claude Code, etc.) → connect via MCP protocol
- A2A clients (future agents) → connect via A2A protocol
- Any HTTP client → connect via REST API

**Subprocess Output**:
- CLI agents don't support server protocols
- Glee invokes them via subprocess (`codex exec`, `claude`, `gemini`)
- Agents run locally with full file access (no Docker isolation)

**Value Proposition**:
- Agent A (supports MCP) → via Glee → can use Agent B (CLI only)
- Agent X (supports A2A) → via Glee → can use Agent Y (CLI only)
- **Glee bridges the protocol gap**

### Agent Registry

Glee maintains a registry of available agents:

```python
class AgentRegistry:
    agents = {
        "claude": {
            "command": "claude",
            "capabilities": ["code", "review", "explain"],
            "config": "~/.claude/"
        },
        "codex": {
            "command": "codex",
            "capabilities": ["code", "review"],
            "exec_mode": "codex exec --json --full-auto"
        },
        "gemini": {
            "command": "gemini",
            "capabilities": ["code", "review"]
        },
        "opencode": {
            "command": "opencode",
            "capabilities": ["code"]
        },
        "crush": {
            "command": "crush",
            "capabilities": ["code"]
        }
    }
```

### Memory Layer

The memory layer provides persistent, searchable storage:

```
┌─────────────────────────────────────────────────────────┐
│                    Memory Layer                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Project Memory                                          │
│  ├── Architecture decisions & rationale                 │
│  ├── Code conventions & style guide                     │
│  ├── Tech stack & dependencies                          │
│  └── Historical context                                  │
│                                                          │
│  Review Memory                                           │
│  ├── Past review feedback                               │
│  ├── Common issues & patterns                           │
│  ├── Resolution history                                  │
│  └── Quality metrics                                     │
│                                                          │
│  Session Memory                                          │
│  ├── Current workflow state                             │
│  ├── Agent interactions                                  │
│  └── Pending actions                                     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Key Feature**: Project ID is stable. Renaming folders doesn't lose history.

```yaml
# glee.yaml
project:
  id: 550e8400-e29b-41d4-a716-446655440000  # UUID, never changes
  name: my-project  # Display name, can change
  aliases:
    - /Users/yumin/old-path/my-project
    - /Users/yumin/new-path/my-project
```

---

## Core Features

### 1. Multi-Agent Review Loop

The primary use case: get a second opinion from another agent.

```
┌──────────────────────────────────────────────────────────┐
│  1. Agent A writes code                                   │
└─────────────────────────────┬────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────┐
│  2. Glee sends to Agent B for review                     │
└─────────────────────────────┬────────────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  Review Result  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   approved    │   │  has_issues   │   │ needs_human   │
│   ✓ Done      │   │  → Fix & Loop │   │  → Ask User   │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 2. Intelligent Review Protocol

Not just "review this code" — structured, professional review:

```json
{
  "checklist": {
    "security": ["input validation", "auth checks", "sql injection"],
    "performance": ["n+1 queries", "caching", "async operations"],
    "maintainability": ["naming", "complexity", "documentation"]
  },
  "severity_levels": ["critical", "warning", "suggestion"],
  "output_format": "structured_json"
}
```

### 3. Role-Based Agent Assignment

Different agents for different tasks:

```yaml
agents:
  - name: claude
    role: backend-coder
    focus: ["api", "database", "business-logic"]

  - name: gemini
    role: frontend-coder
    focus: ["react", "css", "accessibility"]

  - name: codex
    role: reviewer
    focus: ["security", "performance", "best-practices"]

  - name: claude
    role: security-auditor
    focus: ["owasp", "vulnerabilities", "compliance"]
```

### 4. Workflow Engine

Define custom multi-agent workflows:

```yaml
workflows:
  full-review:
    steps:
      - agent: codex
        action: review
        focus: [security, performance]
      - agent: claude
        action: review
        focus: [architecture, maintainability]
      - gate: all_approved

  security-audit:
    steps:
      - agent: claude
        action: security-scan
      - agent: codex
        action: vulnerability-check
      - human: approve
```

---

## CLI Commands

```bash
# Core commands
glee start                    # Start Glee daemon
glee stop                     # Stop Glee daemon
glee status                   # Show running agents & status

# Agent management
glee connect <agent> --role <role>   # Connect an agent
glee disconnect <agent>              # Disconnect an agent
glee agents                          # List connected agents

# Workflow
glee review [files]           # Trigger review workflow
glee workflow run <name>      # Run a custom workflow

# Memory
glee memory show              # Show project memory
glee memory add <key> <value> # Add to memory
glee memory search <query>    # Search memory

# Config
glee init                     # Initialize glee.yaml
glee config                   # Show current config
```

---

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Language | Python | Ecosystem, LangGraph support |
| Package Manager | uv | Fast, modern |
| Orchestration | LangGraph | State management, workflows |
| Types | Pydantic | Validation, serialization |
| Database | PostgreSQL + pgvector | Memory storage, vector search |
| CLI | Click/Typer | User-friendly CLI |

---

## Docker Compose (Database Only)

```yaml
# compose.yml
services:
  db:
    image: pgvector/pgvector:pg17
    container_name: glee-db
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test:
        - CMD-SHELL
        - pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}
      interval: 10s
      timeout: 5s
      retries: 5

  pgweb:
    image: sosedoff/pgweb
    container_name: glee-pgweb
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}?sslmode=disable
    ports:
      - "8081:8081"
    depends_on:
      db:
        condition: service_healthy

networks:
  glee-network:
    driver: bridge
```

---

## Project Structure

```
glee/
├── glee/
│   ├── __init__.py
│   ├── __main__.py           # CLI entry point
│   ├── cli/
│   │   ├── main.py           # CLI commands
│   │   ├── start.py          # glee start
│   │   ├── connect.py        # glee connect
│   │   └── review.py         # glee review
│   ├── core/
│   │   ├── orchestrator.py   # Agent orchestration
│   │   ├── registry.py       # Agent registry
│   │   └── workflow.py       # Workflow engine
│   ├── agents/
│   │   ├── base.py           # Agent interface
│   │   ├── claude.py         # Claude Code adapter
│   │   ├── codex.py          # Codex adapter
│   │   └── gemini.py         # Gemini adapter
│   ├── memory/
│   │   ├── store.py          # Memory abstraction
│   │   ├── postgres.py       # PostgreSQL backend
│   │   └── vector.py         # Vector search
│   ├── review/
│   │   ├── protocol.py       # Review protocol
│   │   ├── checklists.py     # Review checklists
│   │   └── parser.py         # Feedback parser
│   └── db/
│       └── migrations/       # Alembic migrations
├── docs/
│   ├── VISION.md
│   └── PRD.md
├── compose.yml               # Database only
├── pyproject.toml
└── glee.example.yaml
```

---

## V1 Scope

**Goal**: A working multi-agent review loop that's easy to install and use.

### Must Have
- [ ] `glee start` / `glee stop` daemon
- [ ] `glee connect <agent>` for Claude, Codex
- [ ] `glee review` triggers review workflow
- [ ] Basic review loop (code → review → fix → repeat)
- [ ] PostgreSQL memory storage
- [ ] File-based fallback (no database required)

### Nice to Have
- [ ] `glee.yaml` project config
- [ ] Multiple reviewer agents
- [ ] Custom review checklists

### Out of Scope (V2+)
- Vector search / RAG
- Team features
- GitHub integration
- Knowledge marketplace

---

## Success Metrics

1. **Time to first review**: < 5 minutes from install
2. **Review quality**: Catches issues that single agent misses
3. **Memory value**: Context persists across sessions, survives folder renames
4. **Agent agnostic**: Works with any CLI-based coding agent

---

## Open Questions

1. ~~**How does Glee communicate with agents?**~~ ✅ Resolved
   - **Input**: Glee exposes MCP Server + A2A Server + REST API
   - **Output**: Glee invokes CLI agents via subprocess

2. ~~**How does Glee intercept agent output?**~~ ✅ Resolved
   - Subprocess captures stdout/stderr directly
   - Use `--json` flags where available (e.g., `codex exec --json`)

3. ~~**Should Glee have a TUI/Dashboard?**~~ ✅ Resolved
   - **Web UI** (not TUI) — more accessible, broader audience
   - Show agent status, review progress, memory stats
   - Served via FastAPI at `/dashboard`

4. ~~**A2A implementation priority?**~~ ✅ Resolved
   - V1 supports both MCP and A2A
   - Both protocols are straightforward to implement

---

*Glee: The Conductor for Your AI Orchestra.*
