# Glee Memory System

Glee Memory provides persistent project knowledge that survives across sessions. It combines vector search for semantic similarity with structured storage for fast lookups.

## Storage Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Vector | LanceDB | Semantic similarity search |
| Structured | DuckDB | SQL queries, category filtering |
| Embeddings | fastembed (BAAI/bge-small-en-v1.5) | Local embedding generation |

All data is stored in `.glee/`:
- `memory.lance/` - Vector embeddings
- `memory.duckdb` - Structured data

## Categories

Memories are organized by category. Standard categories:

| Category | Use For |
|----------|---------|
| `architecture` | System design, module structure, data flow |
| `convention` | Coding standards, naming patterns, file organization |
| `review` | Common review feedback, recurring issues |
| `decision` | Technical decisions and rationale |

**Custom categories are supported.** Use any string as a category name (e.g., `security`, `api-design`, `testing`).

## CLI Commands

```bash
# Add a memory
glee memory add architecture "API uses REST with versioned endpoints /v1/*"
glee memory add convention "Use snake_case for Python, camelCase for TypeScript"
glee memory add my-custom-category "Custom category content"

# List memories
glee memory list                    # All memories
glee memory list --category architecture  # Filter by category

# Search (semantic similarity)
glee memory search "how do we handle authentication"
glee memory search "error handling" --category convention

# Get formatted overview (for context injection)
glee memory overview

# Delete
glee memory delete abc123           # Delete by ID
glee memory delete-category review  # Delete all in category
glee memory delete-all              # Delete everything

# Statistics
glee memory stats
```

Top-level shortcut:
```bash
glee overview  # Same as 'glee memory overview'
```

## MCP Tools

When Claude Code runs in a Glee project, these tools are available:

| Tool | Description |
|------|-------------|
| `glee_memory_bootstrap` | Bootstrap memory by gathering project docs and structure for analysis |
| `glee_memory_add` | Add a memory with category and content |
| `glee_memory_list` | List memories, optionally filtered by category |
| `glee_memory_search` | Semantic search across memories |
| `glee_memory_overview` | Get formatted overview for context |
| `glee_memory_delete` | Delete a memory by ID |
| `glee_memory_delete_category` | Delete all memories in a category |
| `glee_memory_delete_all` | Delete all memories |
| `glee_memory_stats` | Get memory statistics |

### Memory Bootstrap

`glee_memory_bootstrap` is special - it doesn't require an external LLM API. It gathers:

1. **Documentation**: README.md, CLAUDE.md, CONTRIBUTING.md, docs/
2. **Package config**: pyproject.toml, package.json, Cargo.toml, go.mod
3. **Directory structure**: Top 2 levels, excluding noise

Then returns this context with instructions. Claude Code (already an LLM) analyzes it and calls `glee_memory_add` to populate memories for architecture, conventions, dependencies, and decisions.

## Auto-Injection

When you run `glee init --agent claude`, Glee registers a SessionStart hook in `.claude/settings.local.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|compact",
        "hooks": [
          {
            "type": "command",
            "command": "glee memory overview 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

This injects the memory overview when Claude Code:
- **Starts** a new session
- **Resumes** an existing session
- **Compacts** context (summarization)

## Usage Patterns

### Building Project Memory

As you work, add important context:

```bash
# After making architectural decisions
glee memory add decision "Chose PostgreSQL over MongoDB for ACID compliance"

# When establishing patterns
glee memory add convention "All API errors return {error: string, code: number}"

# After reviews reveal patterns
glee memory add review "Always check null before accessing nested properties"
```

### Semantic Search

Find relevant memories even with different wording:

```bash
# Finds memories about authentication, auth, login, etc.
glee memory search "user login flow"

# Finds memories about error handling patterns
glee memory search "what to do when API fails"
```

### Managing Memory Conflicts

If old information conflicts with new:

1. Delete the outdated memory: `glee memory delete <id>`
2. Add the updated information: `glee memory add <category> "<new content>"`

There's no `update` command - vectors must be regenerated when content changes, so delete + add is the correct workflow.

## Data Model

Each memory entry contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | 8-character UUID |
| `category` | string | Category name |
| `content` | string | The memory content |
| `metadata` | JSON | Optional metadata |
| `created_at` | datetime | Creation timestamp |
| `vector` | float[] | 384-dim embedding (LanceDB only) |

## Limitations

- **Personal only**: Memories are stored locally in `.glee/`, not shared across team
- **No versioning**: Old content is deleted, not archived
- **No conflict resolution**: Users manage conflicts manually

## Files

```
.glee/
├── memory.lance/     # Vector database
├── memory.duckdb     # Structured database
└── config.yml        # Project config
```
