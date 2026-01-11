# Claude-Mem Analysis

Deep dive into Claude-Mem's architecture and what Glee can learn from it.

> Analysis of [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) - A Claude Code plugin providing persistent memory across sessions.

## Overview

**Claude-Mem** is a **production-grade memory system**, not a simple JSON notepad. It uses SQLite with FTS5, ChromaDB for vector search, and Claude Agent SDK for AI-powered observation synthesis.

Key capabilities:
- Captures tool usage during sessions via lifecycle hooks
- Uses AI to compress observations into structured memory
- Injects relevant context into future sessions
- Provides search tools for querying project history

## Technology Stack

| Layer | Technology |
|-------|------------|
| Language | TypeScript (ES2022) |
| Runtime | Node.js 18+ / Bun 1.0+ |
| Database | SQLite 3 (bun:sqlite) |
| Vector DB | ChromaDB (optional) |
| Search | FTS5 full-text search |
| HTTP Server | Express.js |
| Real-time | Server-Sent Events (SSE) |
| UI | React 18 |
| AI SDK | @anthropic-ai/claude-agent-sdk |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────┐
│  Claude Code    │────▶│   Hooks (6)      │────▶│   Worker Service        │
│                 │     │   (TypeScript)   │     │   (localhost:37777)     │
└─────────────────┘     └──────────────────┘     └───────────┬─────────────┘
                                                            │
                        ┌───────────────────────────────────┼───────────────────────────────────┐
                        │                                   │                                   │
                        ▼                                   ▼                                   ▼
              ┌─────────────────┐                 ┌─────────────────┐                 ┌─────────────────┐
              │     SQLite      │                 │    ChromaDB     │                 │  Claude Agent   │
              │  (FTS5 search)  │                 │ (vector search) │                 │      SDK        │
              └─────────────────┘                 └─────────────────┘                 └─────────────────┘
```

### Detailed Component View

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code Session                       │
├─────────────────────────────────────────────────────────────────┤
│  Hooks (6 lifecycle events)                                      │
│  ├── SessionStart    → context-hook.ts (inject ~250 tokens)      │
│  ├── UserPromptSubmit → new-hook.ts (create session)             │
│  ├── PostToolUse     → save-hook.ts (capture tool execution)     │
│  ├── Stop            → summary-hook.ts (generate summary)        │
│  └── SessionEnd      → cleanup-hook.ts (mark complete)           │
├─────────────────────────────────────────────────────────────────┤
│  Worker Service (Bun, port 37777)                                │
│  ├── /api/sessions/observations  → Store compressed observations │
│  ├── /api/sessions/summarize     → Generate session summary      │
│  ├── /api/search                 → Full-text + vector search     │
│  ├── /api/timeline               → Chronological context         │
│  └── /api/observations/batch     → Fetch by IDs                  │
├─────────────────────────────────────────────────────────────────┤
│  Storage                                                         │
│  ├── SQLite (~/.claude-mem/claude-mem.db)                        │
│  └── Chroma (~/.claude-mem/chroma/) - Vector embeddings          │
├─────────────────────────────────────────────────────────────────┤
│  MCP Server (search tools for Claude)                            │
│  ├── __IMPORTANT     → Workflow documentation (always visible)   │
│  ├── search          → Index results with IDs                    │
│  ├── timeline        → Context around observations               │
│  └── get_observations → Full details by IDs                      │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
claude-mem/
├── src/
│   ├── hooks/              # 6 lifecycle hooks
│   │   ├── new-hook.ts     # UserPromptSubmit - creates session
│   │   ├── save-hook.ts    # PostToolUse - captures observations
│   │   ├── summary-hook.ts # Stop - generates summary
│   │   ├── context-hook.ts # SessionStart - injects context
│   │   └── cleanup-hook.ts # SessionEnd - marks complete
│   ├── sdk/                # Agent SDK integration
│   │   ├── prompts.ts      # XML prompt builders
│   │   └── parser.ts       # XML response parser
│   ├── services/
│   │   ├── worker/         # Express HTTP routes
│   │   │   ├── SDKAgent.ts # Claude Agent SDK query loop
│   │   │   └── SearchManager.ts
│   │   ├── sqlite/         # Database layer
│   │   │   └── SessionStore.ts
│   │   └── sync/           # ChromaDB sync
│   ├── ui/viewer/          # React web interface
│   └── shared/             # Utilities
├── plugin/                 # Built artifacts
│   └── skills/mem-search/  # Skill definition
└── docs/                   # Documentation
```

**Data Location:**
- Database: `~/.claude-mem/claude-mem.db`
- Vector DB: `~/.claude-mem/chroma/`
- Settings: `~/.claude-mem/settings.json`

## Database Schema

### Core Tables

**1. `sdk_sessions`** - Session tracking

```sql
CREATE TABLE sdk_sessions (
    id INTEGER PRIMARY KEY,
    claude_session_id TEXT UNIQUE,
    sdk_session_id TEXT,
    project TEXT,
    user_prompt TEXT,
    started_at TEXT,
    started_at_epoch INTEGER,
    completed_at TEXT,
    status TEXT  -- 'active' | 'completed'
);
-- Indexed on: claude_id, sdk_id, project, status, started_at
```

**2. `observations`** - Extracted work items

```sql
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    sdk_session_id TEXT,
    project TEXT,
    text TEXT,
    type TEXT,              -- decision|bugfix|feature|refactor|discovery|change
    title TEXT,
    subtitle TEXT,
    narrative TEXT,
    facts TEXT,             -- JSON array
    concepts TEXT,          -- JSON array
    files_read TEXT,        -- JSON array
    files_modified TEXT,    -- JSON array
    prompt_number INTEGER,
    discovery_tokens INTEGER,
    created_at TEXT,
    created_at_epoch INTEGER
);
-- Indexed on: sdk_session_id, project, type, created_at
```

**3. `session_summaries`** - Session-level summaries

```sql
CREATE TABLE session_summaries (
    id INTEGER PRIMARY KEY,
    sdk_session_id TEXT UNIQUE,
    project TEXT,
    request TEXT,           -- What user asked
    investigated TEXT,      -- What was explored
    learned TEXT,           -- Key learnings
    completed TEXT,         -- What got done
    next_steps TEXT,        -- Follow-up items
    notes TEXT,
    prompt_number INTEGER,
    discovery_tokens INTEGER,
    created_at TEXT,
    created_at_epoch INTEGER
);
```

**4. `user_prompts`** - Raw user requests

```sql
CREATE TABLE user_prompts (
    id INTEGER PRIMARY KEY,
    claude_session_id TEXT,
    prompt_number INTEGER,
    prompt_text TEXT,
    sdk_session_id TEXT,
    project TEXT,
    created_at TEXT,
    created_at_epoch INTEGER
);
```

**5. `pending_messages`** - Queue for SDK processing

```sql
CREATE TABLE pending_messages (
    id INTEGER PRIMARY KEY,
    sdk_session_id TEXT,
    message_text TEXT,
    created_at_epoch INTEGER
);
```

### FTS5 Virtual Table

```sql
CREATE VIRTUAL TABLE observations_fts USING fts5(
    title, subtitle, narrative, text, facts, concepts,
    content='observations',
    content_rowid='rowid'
);
-- Triggers auto-sync inserts/updates
```

### Database Optimizations

```sql
PRAGMA journal_mode = WAL;      -- Concurrent access
PRAGMA synchronous = NORMAL;    -- Balance durability/speed
PRAGMA foreign_keys = ON;       -- Referential integrity
PRAGMA mmap_size = 256MB;       -- Memory-mapped I/O
PRAGMA cache_size = 10000;      -- 10,000 pages cache
```

## Session Lifecycle

```
Step 1: SessionStart → context-hook.ts
    ↓ Injects ~250 tokens of previous context
    ↓ Calls /api/context/inject

Step 2: UserPromptSubmit → new-hook.ts
    ↓ Creates sdk_sessions entry
    ↓ Saves raw prompt to user_prompts
    ↓ Initializes SDK agent session

Step 3: PostToolUse → save-hook.ts (fires 100+ times)
    ↓ HTTP POST /api/sessions/observations
    ↓ Creates pending_message in DB
    ↓ Fire-and-forget (non-blocking)

Step 4: Worker processes observations
    ↓ SDKAgent reads pending messages
    ↓ Sends to Claude Agent SDK with XML prompts
    ↓ Parses XML response → observations table
    ↓ Syncs to ChromaDB

Step 5: Stop → summary-hook.ts
    ↓ Extracts last messages from transcript
    ↓ Calls /api/sessions/summarize
    ↓ SDK generates structured summary

Step 6: SessionEnd → cleanup-hook.ts
    ↓ Marks session as 'completed'
```

## AI Compression Pipeline

Claude-Mem uses a **secondary AI agent** to compress raw tool observations into structured memory:

```
Tool Execution (Claude Code)
    ↓
PostToolUse Hook (save-hook.ts)
    ↓
HTTP POST /api/sessions/observations
    ↓
Worker: Creates pending_message
    ↓
SDKAgent: Processes via Claude Agent SDK
    ↓
SDK Prompt (XML template):
    <tool_observation>
      <tool>Read</tool>
      <input>src/auth.ts</input>
      <output>JWT validation code...</output>
    </tool_observation>
    ↓
Claude Response (XML):
    <observation>
      <type>discovery</type>
      <title>Found JWT validation in auth.ts</title>
      <facts>
        <fact>Uses RS256 algorithm</fact>
        <fact>Token expires in 24h</fact>
      </facts>
      <files_read>
        <file>src/auth.ts</file>
      </files_read>
    </observation>
    ↓
Parser extracts XML blocks
    ↓
Database: observations table
    ↓
ChromaDB: Vector sync
```

### Observation Schema

```typescript
interface Observation {
  type: 'bugfix' | 'feature' | 'refactor' | 'change' | 'discovery' | 'decision';
  title: string;           // Short, action-oriented
  subtitle: string;        // One sentence (max 24 words)
  facts: string[];         // Self-contained statements
  narrative: string;       // Full context
  concepts: string[];      // 'how-it-works', 'gotcha', 'pattern', etc.
  files_read: string[];
  files_modified: string[];
}
```

### Observation Types

| Type | Description | Emoji |
|------|-------------|-------|
| `bugfix` | Something was broken, now fixed | 🔴 |
| `feature` | New capability or functionality added | 🟣 |
| `refactor` | Code restructured, behavior unchanged | 🔄 |
| `change` | Generic modification (docs, config, misc) | ✅ |
| `discovery` | Learning about existing system | 🔵 |
| `decision` | Architectural/design choice with rationale | ⚖️ |

### Concept Categories

| Concept | Description |
|---------|-------------|
| `how-it-works` | Understanding mechanisms |
| `why-it-exists` | Purpose or rationale |
| `what-changed` | Modifications made |
| `problem-solution` | Issues and their fixes |
| `gotcha` | Traps or edge cases |
| `pattern` | Reusable approach |
| `trade-off` | Pros/cons of a decision |

## Search Architecture (Hybrid)

**Three Search Paths:**

| Path | When Used | Method |
|------|-----------|--------|
| Filter-only | No search text | SQLite with date filters |
| Semantic | Text query | ChromaDB + SQLite |
| Full-text | Chroma unavailable | FTS5 fallback |

**Hybrid Search Flow:**

```
Query: "auth implementation"
    ↓
1. ChromaDB semantic search (relevance ranking)
    ↓
2. Filter by 90-day recency window
    ↓
3. Categorize by doc_type (observation/session/prompt)
    ↓
4. Fetch full records from SQLite
    ↓
5. Format with token estimates:
   | ID | Time | T | Title | Read | Work |
   |#123| 3:48 | 🟣 | JWT auth | ~75 | 🛠️ 450 |
```

### 3-Layer Search Pattern (Token Efficient)

```
1. search(query)
   └─→ Returns index with IDs (~50-100 tokens/result)

2. timeline(anchor=ID)
   └─→ Returns chronological context around observation

3. get_observations(ids=[...])
   └─→ Returns full details (~500-1000 tokens/result)

Result: ~10x token savings by filtering before fetching
```

### MCP Tools

```typescript
// Tool 1: Always visible workflow documentation
__IMPORTANT: "3-LAYER WORKFLOW (ALWAYS FOLLOW):
1. search(query) → Get index with IDs
2. timeline(anchor=ID) → Get context around results
3. get_observations([IDs]) → Fetch full details ONLY for filtered IDs"

// Tool 2: Search index
search(query, limit, project, type, dateStart, dateEnd)
// Returns: Table with IDs, titles, dates

// Tool 3: Timeline context
timeline(anchor=ID, depth_before=3, depth_after=3)
// Returns: Chronological context

// Tool 4: Full details
get_observations(ids=[123, 456])
// Returns: Complete observation details
```

## HTTP API Endpoints

**Search Endpoints:**

| Endpoint | Description |
|----------|-------------|
| `GET /api/search` | Unified semantic search |
| `GET /api/timeline` | Temporal context around anchor |
| `GET /api/decisions` | Filter type=decision |
| `GET /api/changes` | Filter type=change |
| `GET /api/search/observations` | FTS5 on observations |
| `GET /api/search/sessions` | FTS5 on summaries |
| `GET /api/search/prompts` | FTS5 on user prompts |
| `GET /api/search/by-concept` | Filter by concept tags |
| `GET /api/search/by-file` | Filter by files touched |

**Context Endpoints:**

| Endpoint | Description |
|----------|-------------|
| `GET /api/context/inject` | Get context for session start |
| `GET /api/context/recent` | Recent observations for project |
| `GET /api/context/timeline` | Timeline around time point |

**Session Endpoints:**

| Endpoint | Description |
|----------|-------------|
| `POST /api/sessions/init` | Initialize session |
| `POST /api/sessions/observations` | Record observation |
| `POST /api/sessions/summarize` | Generate summary |
| `POST /api/sessions/complete` | Mark complete |

## Key Features

### 1. Progressive Disclosure

- **Context Index** (~250 tokens): Titles, types, timestamps, files
- **Full Details**: Fetched on-demand via mem-search skill
- **Token Savings**: ~2,250 tokens vs injecting everything

### 2. Privacy Controls

```xml
<private>sensitive content</private>  <!-- Excluded from storage -->
<claude-mem-context>...</claude-mem-context>  <!-- Prevents recursive storage -->
```

- Tag stripping at hook layer (edge processing)

### 3. Token Metrics

- `discovery_tokens`: Tokens spent discovering observation
- Read tokens: chars ÷ 4 estimate
- Work type indicators: 🔍 research, 🛠️ building, ⚖️ deciding

### 4. Mode System

- Pluggable behaviors via ModeManager
- Different observation types per mode
- Concept tags vary by mode

### Mode Configuration Example

```json
{
  "name": "Code Development",
  "observation_types": [
    { "id": "bugfix", "label": "Bug Fix", "emoji": "🔴" },
    { "id": "feature", "label": "Feature", "emoji": "🟣" }
  ],
  "observation_concepts": [
    { "id": "how-it-works", "label": "How It Works" },
    { "id": "gotcha", "label": "Gotcha" }
  ],
  "prompts": {
    "system_identity": "You are Claude-Mem, a specialized observer...",
    "observer_role": "Your job is to monitor a different Claude Code session...",
    "recording_focus": "Focus on deliverables and capabilities...",
    "skip_guidance": "Skip routine operations..."
  }
}
```

## Session Summaries

At session end (Stop hook), Claude-Mem generates a summary:

```xml
<summary>
  <request>[What the user asked for]</request>
  <investigated>[What was explored]</investigated>
  <learned>[What was discovered]</learned>
  <completed>[What shipped/changed]</completed>
  <next_steps>[Current trajectory]</next_steps>
  <notes>[Additional insights]</notes>
</summary>
```

## Web Viewer UI

Claude-Mem includes a React-based web viewer at `http://localhost:37777`:

- Real-time memory stream (SSE)
- Session timeline visualization
- Search interface
- Settings management
- Token economics visibility

## Comparison: Claude-Mem vs Glee Memory

| Aspect | Claude-Mem | Glee Memory |
|--------|------------|-------------|
| **Installation** | Claude Code plugin marketplace | MCP server via `glee init` |
| **Hooks** | 6 lifecycle hooks | 2 hooks (SessionStart, SessionEnd) |
| **Compression** | AI-powered (Claude API) | Direct storage |
| **Storage** | SQLite + Chroma vectors | LanceDB + DuckDB |
| **Search** | 3-layer progressive disclosure | Single query |
| **UI** | Web viewer at :37777 | CLI only |
| **Token visibility** | Shows cost in UI | Hidden |
| **Focus** | Memory compression | Multi-agent orchestration + memory |

## What Glee Can Learn

### 1. PostToolUse Hook

Claude-Mem captures every tool execution in real-time (fires 100+ times per session). Glee only has session start/end hooks.

**Glee's approach**: Real-time capture is overkill. Session-end summarization is sufficient and less intrusive. The overhead of 100+ hook invocations per session adds latency.

### 2. AI Compression

Claude-Mem uses a secondary AI agent to compress tool outputs into structured observations.

**Glee's approach**: AI compression adds latency. For now, prefer fast direct storage over slow LLM extraction. Speed matters more than perfect structure. Session-end summarization (which Glee already does) is a better tradeoff - one AI call at the end vs. continuous processing.

### 3. Progressive Search

Claude-Mem's 3-layer pattern saves tokens by filtering before fetching.

**Opportunity**: Modify `glee_memory_search` to return IDs first, add `glee_memory_get` for full details.

### 4. Observation Schema

Structured types (bugfix, feature, discovery) make memory more queryable.

**Opportunity**: Adopt similar schema for Glee's memory entries.

### 5. Token Economics

Claude-Mem shows users how much context is being injected.

**Opportunity**: Add token counting to `glee warmup-session` output.

### 6. Web Viewer

Real-time visibility into memory stream helps debugging and trust.

**Opportunity**: Add `glee viewer` or integrate into `glee watch` TUI.

### 7. Database Optimizations

SQLite pragmas (WAL mode, mmap, cache tuning) for performance.

**Opportunity**: Apply similar optimizations to DuckDB/LanceDB.

## Implementation Recommendations

### Worth Adopting

1. **Progressive search API** - Split into index + fetch endpoints (token savings)
2. **Token visibility** - Show context injection cost in warmup output
3. **Database pragmas** - WAL mode, cache tuning for performance
4. **Structured observation schema** - Add `type`, `title` fields (without AI extraction)

### Not Worth It (For Now)

- **PostToolUse hook** - Too much overhead, 100+ invocations per session
- **Real-time AI compression** - Adds latency, Glee's session-end summary is enough
- **Chroma/vector DB** - LanceDB already handles this, no need for extra complexity

### Future Consideration

- **Web viewer** - Nice for debugging, but `glee watch` TUI may be sufficient
- **Mode system** - Per-project templates, but adds complexity

## Glee Differentiators

While learning from Claude-Mem, Glee has unique strengths:

- **Multi-agent orchestration** - Claude-Mem is memory-only; Glee orchestrates reviewers
- **Universal tool support** - Not just Claude Code (Codex, Gemini, etc.)
- **LanceDB** - Lighter than ChromaDB (no Python runtime dependency)
- **DuckDB for relationships** - Claude-Mem lacks entity-relationship graphs
- **Simpler architecture** - Single sidecar vs Worker/MCP separation

## Resources

- GitHub: https://github.com/thedotmack/claude-mem
- Docs: https://docs.claude-mem.ai
- Author: Alex Newman (@thedotmack)
- License: AGPL-3.0
