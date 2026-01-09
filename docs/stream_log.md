# Stream Logging

## The Problem

When Glee runs as an MCP server, **stderr is swallowed** by the MCP protocol. Users see nothing in the terminal while waiting for agent responses.

```
Claude Code → MCP → Glee → spawns Codex → stdout/stderr
                ↑
          MCP swallows stderr
          User sees nothing
```

## Why Agents Use stderr

CLI design convention:

| Stream | Purpose |
|--------|---------|
| stdout | Final result, structured data (JSON) |
| stderr | Progress, reasoning, logs, transient info |

This separation allows piping results without polluting them with progress output:

```bash
claude "question" | jq .   # stdout is clean JSON
                           # stderr shows thinking (doesn't break pipe)
```

## Glee's Solution

Since Glee spawns agents via subprocess, **Glee can capture both streams** even though MCP can't display them.

### Log Location

```
.glee/stream_logs/
├── stdout-20260109.log   # Agent stdout (reasoning, results)
├── stderr-20260109.log   # Agent stderr (progress, errors)
├── stdout-20260108.log   # Previous day
└── ...
```

### Daily Rotation

- Logs are named with date: `{stream_type}-YYYYMMDD.log`
- New file each day automatically
- Old files can be cleaned up manually

### How to Watch

In a separate terminal:

```bash
# Watch agent reasoning
tail -f .glee/stream_logs/stdout-$(date +%Y%m%d).log

# Watch agent errors/progress
tail -f .glee/stream_logs/stderr-$(date +%Y%m%d).log

# Watch both
tail -f .glee/stream_logs/*.log
```

## MCP Limitation

MCP protocol doesn't support streaming responses or progress notifications. The client blocks until the tool call completes.

**Why we can't fix this:**
- MCP is a protocol spec (now under Linux Foundation)
- Adding streaming would require protocol changes
- Out of Glee's control

**Workarounds:**
1. `tail -f` in separate terminal (current solution)
2. Future: TUI/dashboard that tails logs
3. Future: MCP protocol adds streaming support

## Implementation

See `glee/agents/base.py`:

```python
def write_to_log(stream_type: str, line: str) -> None:
    log_dir = self.project_path / ".glee" / "stream_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    log_path = log_dir / f"{stream_type}-{date_str}.log"
    with open(log_path, "a") as f:
        f.write(line)
        f.flush()
```

Both stdout and stderr from subprocess are captured and written to their respective log files.
