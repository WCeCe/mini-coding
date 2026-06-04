&nbsp;
# Mini-Coding-Agent

This folder contains a small standalone coding agent:

- package: `mini_coding_agent/` (implementation)
- CLI entry: `mini_coding_agent.py` or `mini-coding-agent`

It is a minimal local agent loop with:

- workspace snapshot collection
- stable prompt plus turn state
- structured tools
- approval handling for risky tools
- **change governance** for file writes (diff preview, checkpoint, rollback)
- **tool-boundary hooks** for observability and extension (`pre_tool` / `post_tool`)
- **terminal tool trace**, shell audit alerts, and **YAML-configured built-in hooks** (Phase 2.1)
- **task planning** with structured `make_plan` and optional `--plan-first` (Phase 3)
- **Skills (Phase 4)** — reusable workflow packs from `.mini-coding-agent/skills/` with two-stage loading (`load_skill`, `--skills`)
- **Graph Harness (Phase 5)** — optional template-driven pipeline: LLM Gate (5 intents), DAG execution, offline RIG, open-loop fallback (`--harness`, `--gate-log`, `rig build`)
- transcript and memory persistence
- bounded delegation

The model backend is currently based on Ollama.

<a href="https://magazine.sebastianraschka.com/p/components-of-a-coding-agent">
  <img src="https://substack-post-media.s3.amazonaws.com/public/images/49b97718-57f4-4977-99c8-8ad5c4d32af3_1548x862.png" width="500px">
</a>

<br>

**[The detailed tutorial: Components of a Coding Agent](https://magazine.sebastianraschka.com/p/components-of-a-coding-agent)**


&nbsp;
## Six Core Components

<a href="https://magazine.sebastianraschka.com/p/components-of-a-coding-agent">
  <img alt="Six core components of a coding agent" src="https://sebastianraschka.com/images/github/mini-coding-agent/six-components.webp" width="500px">
</a>

This coding harness is organized around six practical building blocks:

1. **Live repo context**  
   The agent collects stable workspace facts upfront, such as repo layout, instructions, and git state.
2. **Prompt shape and cache reuse**  
   A stable prompt prefix, which is separate from the changing request, transcript, and memory so repeated model calls can reuse the static parts efficiently.
3. **Structured tools, validation, and permissions**  
   The model works through named tools with checked inputs, workspace path validation, and approval gates instead of free-form arbitrary actions.
4. **Context reduction and output management**  
   Long outputs are clipped, repeated reads are deduplicated, and older transcript entries are compressed to keep prompt size under control.
5. **Transcripts, memory, and resumption**  
   The runtime keeps both a full durable transcript and a smaller working memory so sessions can be resumed while preserving important state via working memory.
6. **Delegation and bounded subagents**  
   Scoped subtasks can be delegated to helper agents that inherit enough context to help (but operate within limits).

&nbsp;
## Requirements

You need:

- Python 3.10+
- Ollama installed
- an Ollama model pulled locally

Optional:

- `uv` for environment management and the `mini-coding-agent` CLI entry point

This project depends on the Python standard library plus **PyYAML** (for optional hook configuration). Install with `pip install -e .` or use `uv`, then run `python mini_coding_agent.py` or the `mini-coding-agent` CLI entry point.

&nbsp;
## Install Ollama

Install Ollama on your machine so the `ollama` command is available in your shell.

Official installation link: [ollama.com/download](https://ollama.com/download)

Then verify:

```bash
ollama --help
```

Start the server:

```bash
ollama serve
```

In another terminal, pull a model. Example:

```bash
ollama pull qwen3.5:4b
```

Qwen 3.5 model library:

- [ollama.com/library/qwen3.5](https://ollama.com/library/qwen3.5)

The default in this project is `qwen3.5:4b`. If you have sufficient memory, it is worth trying a larger model such as `qwen3.5:9b` or another larger Qwen 3.5 variant. The agent just sends prompts to Ollama's `/api/generate` endpoint.

&nbsp;
## Project Setup

Clone the repo or your fork and change into it:

```bash
git clone https://github.com/rasbt/mini-coding-agent.git
cd mini-coding-agent
```

If you forked it first, use your fork URL instead:

```bash
git clone https://github.com/<your-github-user>/mini-coding-agent.git
cd mini-coding-agent
```



&nbsp;
## Basic Usage

Start the agent:

```bash
cd mini-coding-agent
uv run mini-coding-agent
```

Without `uv`, run the script directly:

```bash
cd mini-coding-agent
python mini_coding_agent.py
```

By default it uses:

- model: `qwen3.5:4b`
- approval: `ask`

For a concrete usage example, see [EXAMPLE.md](EXAMPLE.md).

&nbsp;
## Approval Modes

Risky tools such as shell commands and file writes are gated by approval.

- `--approval ask`
  prompts before risky actions (default and recommended)
- `--approval auto`
  allows risky actions automatically, including arbitrary command execution and file writes by the model; use only with trusted prompts and trusted repositories
- `--approval never`
  denies risky actions

Example:

```bash
uv run mini-coding-agent --approval auto
```

&nbsp;
## Change Governance

When the agent calls `write_file` or `patch_file`, the runtime applies a **change governance** layer before anything is written to disk. The model still uses the same tool format; governance sits in the execution layer.

### What happens on a file change

1. The agent reads the current file from disk and computes the proposed content in memory.
2. A **unified diff** is shown in the terminal (when `--approval ask` is active).
3. If the git working tree has uncommitted changes, a **read-only warning** is printed before you approve.
4. After you approve, a **checkpoint** is saved under:

   ```text
   .mini-coding-agent/checkpoints/<session-id>/
   ```

5. The file is written with an **atomic replace** (temp file, then rename).
6. If the write fails, the runtime **rolls back** from the checkpoint.

If you **deny** approval, nothing is written and no checkpoint is created.

### Session audit trail

Saved sessions (`.mini-coding-agent/sessions/`) record governance metadata for file tools, including a diff summary, checkpoint id, and whether a rollback occurred. Full diffs are not duplicated into the model prompt; only a short summary is kept in history.

### Approval modes and file tools

| Mode | File change behavior |
|------|----------------------|
| `ask` (default) | Shows unified diff, then prompts `approve this change? [y/n]` |
| `auto` | Skips the prompt; still checkpoints and uses atomic writes |
| `never` | Denies all risky tools, including file writes |

`run_shell` is unchanged: it still prompts with the raw tool arguments, not a diff.

### Known limitations (Phase 1)

- **No rollback for `run_shell`.** Shell commands can change files in ways the agent cannot track, so only `write_file` and `patch_file` are governed.
- **Per-tool rollback only.** If one user request triggers several file tools, each step has its own checkpoint. There is no single undo for the entire request.
- **No automatic `git commit`.** Git integration is read-only (status warnings only).
- **Large diffs** are printed in full to the terminal; there is no pager or Web UI.
- **External edits during a session:** if you manually change a file after the agent wrote it, automatic rollback may skip with an explicit error rather than overwrite your edits.

For a walkthrough that hits file writes and approvals, see [EXAMPLE.md](EXAMPLE.md).

&nbsp;
## Extension & Observability

Phase 2 adds a lightweight **Hook** layer at the tool execution boundary. The model tool format and `parse` behavior are unchanged; hooks sit in the execution layer alongside change governance.

### What hooks do

After a tool call passes validation, the runtime fires a matched pair of events for each `run_tool` invocation:

- **`pre_tool`** — before execution (including diff approval and checkpointing for file tools)
- **`post_tool`** — after execution completes, including error-string returns

Hooks are **observe-only**: they cannot block tools, change arguments, or alter return values. **Approval and change governance still run on their original paths.** If a hook callback raises an exception, the agent **fail-opens** and continues the tool call.

Invalid tool names or failed argument validation do **not** trigger hooks.

### Default trace hook

By default, each `MiniAgent` registers a built-in **trace hook** (`enable_trace_hook=True`). It appends structured entries to the saved session JSON under:

```text
.mini-coding-agent/sessions/<session-id>.json  →  "tool_trace"
```

Each entry includes step number, tool name, success/failure, duration in milliseconds, and whether the tool is marked risky. Risky tools also get a separate **`tool_audit`** list (argument key names only — this is audit logging, not a substitute for `--approval ask`).

Open a session file after a run, or use `/session` in the REPL to find the path.

### Registering custom hooks (programmatic)

Hooks are registered in-process with Python callbacks. This is intended for embedding or tests, not the interactive CLI:

```python
from mini_coding_agent import MiniAgent, SessionStore, WorkspaceContext
from mini_coding_agent.models import FakeModelClient

workspace = WorkspaceContext.build(".")
store = SessionStore(".mini-coding-agent/sessions")
agent = MiniAgent(
    model_client=FakeModelClient([]),
    workspace=workspace,
    session_store=store,
)

def on_pre(ctx):
    print(f"before {ctx.name}")

def on_post(ctx):
    print(f"after {ctx.name}: success={ctx.success}, {ctx.duration_ms:.1f}ms")

agent.register_hook("pre_tool", on_pre)
agent.register_hook("post_tool", on_post)
```

Disable the built-in trace hook when constructing the agent:

```python
MiniAgent(..., enable_trace_hook=False)
```

### Project layout (after Phase 2 refactor)

| Path | Role |
|------|------|
| `mini_coding_agent.py` | Thin CLI launcher (`python mini_coding_agent.py`) |
| `mini_coding_agent/agent.py` | Main agent loop, tools, change governance |
| `mini_coding_agent/hooks/registry.py` | Hook registry and context (ask / llm / tool events) |
| `mini_coding_agent/hooks/plugins/` | **Hook implementations** — add new hooks here |
| `mini_coding_agent/hooks/plugins/trace_hook.py` | Session trace + risky tool audit |
| `mini_coding_agent/hooks/plugins/trace_display_hook.py` | Terminal one-line trace (stderr) |
| `mini_coding_agent/hooks/plugins/shell_audit_hook.py` | `run_shell` pattern warnings + `shell_audit` |
| `mini_coding_agent/hooks/plugins/ask_timing_hook.py` | Per-ask LLM/tool timing jsonl |
| `mini_coding_agent/hooks/builtin.py` | Register built-in hooks from YAML config |

Import from the package as before: `from mini_coding_agent import MiniAgent`.

### Known limitations (Phase 2)

- **Observe-only hooks.** Hooks cannot deny tools or modify args/results; blocking or policy enforcement belongs in the execution layer (e.g. approval), not hooks.
- **Tool boundary only.** There are no `session_start`, `session_end`, or per-model-step hooks in this phase.
- **No external hook plugins.** No `hooks.json`, shell scripts, or dynamic module loading — only in-process Python callbacks.
- **Delegate tracing is split.** A parent `delegate` call gets one trace entry; the child agent has its own session and `tool_trace` for tools it runs internally.
- **Trace is session-local.** There is no separate trace file or Web UI; inspect the session JSON or add your own hook to export elsewhere.

### Phase 2.1: Three-layer hook stack

Phase 2.1 makes the default hooks **visible in the terminal** and **configurable per workspace**, without changing the model tool format or approval flow.

| Layer | What you get |
|-------|----------------|
| **1 — Runtime visibility** | After each tool completes, one line on **stderr**: step, tool name, success/failure, duration (ms). Works in REPL and one-shot mode. |
| **2 — Built-in hooks** | **Session trace** (JSON in the session file), **terminal trace display** (layer 1), and **shell audit** (pattern warnings for `run_shell`). |
| **3 — YAML config** | Enable or disable each built-in hook via `.mini-coding-agent/hooks.yaml`. No external scripts or plugin loading. |

Example terminal output (stderr, separate from the model’s final answer on stdout):

```text
[mini-agent] #1 read_file ok 3.2ms
[mini-agent] #2 run_shell ok 45.1ms
[mini-agent] SHELL AUDIT: matched 'rm -rf' — cmd: rm -rf /tmp/demo
```

#### Approve vs hooks

These roles stay separate:

- **`--approval ask`** (or `auto` / `never`) — **gates risky tools** before they run. You must approve shell commands and file writes when using `ask`.
- **Hooks** — **observe only**. They print trace lines, write session audit fields, and warn on dangerous shell patterns. They do **not** block execution, skip approval, or change tool results.

Shell audit runs **after** `run_shell` completes. A warning does not cancel the command; it adds visibility alongside approval.

#### Session fields (Phase 2.1)

In addition to Phase 2’s `tool_trace` and `tool_audit`, shell pattern hits are stored under:

```text
.mini-coding-agent/sessions/<session-id>.json  →  "shell_audit"
```

Each `shell_audit` entry includes the matched pattern, a clipped command preview, step number, and timestamp.

#### `hooks.yaml` configuration

Default path (under your workspace root):

```text
.mini-coding-agent/hooks.yaml
```

Copy the repo template [`hooks.yaml.example`](.mini-coding-agent/hooks.yaml.example) into that path and edit as needed.

Example:

```yaml
builtin_hooks:
  session_trace: true   # write tool_trace to session JSON
  trace_display: true   # print one stderr line per tool step
  shell_audit: true     # warn on dangerous run_shell patterns

shell_audit:
  warn_patterns:        # case-insensitive regex list
    - "rm -rf"
    - "curl.*\\|.*sh"
```

**Default behavior when the file is missing:** all three built-in hooks are **on**, with the built-in `warn_patterns` shown above.

**Malformed YAML:** the agent still starts (**fail-open**). A short warning is printed to stderr and defaults are used.

**Priority:** explicit CLI flags override YAML; YAML overrides built-in defaults.

| CLI flag | Effect |
|----------|--------|
| `--no-trace-display` | Disable per-tool stderr trace lines |
| `--no-session-trace` | Disable session `tool_trace` JSON |
| `--no-shell-audit` | Disable shell pattern audit hook |
| `--hooks-config PATH` | Use a custom `hooks.yaml` path |

Quiet mode example:

```bash
uv run mini-coding-agent --no-trace-display
```

#### Project layout (Phase 2 / 2.1 — hooks package)

All hook implementations live under `mini_coding_agent/hooks/plugins/`. Add new hooks in that directory and register them from `builtin.py` or via `register_hook`.

| Path | Role |
|------|------|
| `mini_coding_agent/hooks/hook_config.py` | Load `hooks.yaml`, CLI overrides, fail-open defaults |
| `mini_coding_agent/hooks/hooks.yaml.example` | Template; copy to `<workspace>/.mini-coding-agent/hooks.yaml` |
| `mini_coding_agent/hooks/registry.py` | Hook registry and context |
| `mini_coding_agent/hooks/builtin.py` | Register built-in hooks from config |
| `mini_coding_agent/hooks/plugins/` | Hook implementations (add new hooks here) |
| `mini_coding_agent/hooks/plugins/trace_hook.py` | Session trace + risky tool audit |
| `mini_coding_agent/hooks/plugins/trace_display_hook.py` | Terminal one-line trace |
| `mini_coding_agent/hooks/plugins/shell_audit_hook.py` | Shell pattern audit |
| `mini_coding_agent/hooks/plugins/ask_timing_hook.py` | Per-ask timing jsonl |

### Known limitations (Phase 2.1)

- **Shell audit does not block.** Pattern matches produce stderr warnings and session records only; `--approval ask` still controls whether risky tools run.
- **No command denylist enforcement.** Blocking dangerous commands is out of scope; hooks remain observe-only.
- **YAML configures built-in hooks only.** No external Python modules, shell scripts, or `hooks.json` plugins.
- **Invalid regex in `warn_patterns`** is skipped silently (fail-open); other patterns still apply.
- **Terminal trace goes to stderr.** Redirect or disable with `--no-trace-display` / YAML if you need a quiet pipeline.

&nbsp;
## Task Planning (Phase 3)

For complex work, the agent can produce a **task-level plan** (steps with acceptance criteria) before changing files or running shell commands. Planning uses a separate single model call inside the `make_plan` tool — it does not auto-run steps for you.

### `make_plan` vs `delegate`

- **`delegate`** — spawns a bounded **read-only** sub-agent to investigate (multi-step tools).
- **`make_plan`** — one structured planning call that returns a JSON plan (no internal tool loop).

Use investigation tools when you need facts; use `make_plan` when you need a checklist to execute against.

### When to plan

By default the model decides when to plan (prompt rules encourage planning for multi-file changes, vague requests, or when you ask for a plan). You can also force planning for every user request with `--plan-first` (see below).

### Tool: `make_plan`

| Item | Detail |
|------|--------|
| Risk | **Safe** — no approval prompt; does not write files or run shell |
| Parameters | `goal` (required), `context` (optional string, e.g. findings from `read_file` / `search`) |
| Call format | `<tool>{"name":"make_plan","args":{"goal":"add unit tests","context":"read src/foo.py first"}}</tool>` |

On success the tool returns **`规划成功`**, a short summary, and a `<plan_json>...</plan_json>` block. The parsed plan is stored in session memory.

**Plan JSON shape (summary):**

```json
{
  "goal": "string",
  "steps": [
    { "id": "1", "title": "...", "acceptance": "...", "risky_hint": "optional" }
  ],
  "assumptions": ["..."],
  "out_of_scope": ["..."]
}
```

At most **12** steps. Invalid JSON or missing fields produce a clear tool error; **`memory.plan` is not updated** on failure.

### Plan in session memory

Successful plans are saved under:

```text
.mini-coding-agent/sessions/<session-id>.json  →  memory.plan
```

The plan is also injected into the agent prompt via working memory (`memory_text()`). In the REPL, run **`/memory`** to see the current task, **plan summary** (goal and step titles), tracked files, and recent notes.

`/reset` clears the plan along with history and other memory fields.

Plans are **not** written to a separate file on disk in this release.

### `--plan-first`

When this flag is set, each **`ask()`** (one user message in REPL or one-shot CLI) must call **`make_plan` successfully** before the first **risky** tool in that same turn: `write_file`, `patch_file`, or `run_shell`.

If the model tries a risky tool first, the runtime returns an error asking it to call `make_plan` first. Approval and change governance are unchanged — `--plan-first` only adds this ordering gate.

Without `--plan-first`, behavior matches Phase 2: planning is optional.

Example (one-shot):

```bash
uv run mini-coding-agent --plan-first --approval ask "Refactor auth helpers and add pytest coverage"
```

Example (REPL):

```bash
uv run mini-coding-agent --plan-first
```

Then type your task at the `mini-coding-agent>` prompt.

**Note:** satisfaction resets at the start of each new user message. Resuming a session does not skip planning on the next turn unless you omit `--plan-first`.

### Known limitations (Phase 3)

- **No automatic step execution.** The agent is not dispatched step-by-step from the plan; it follows memory and its own tool choices.
- **No step completion tracking.** There is no built-in “mark step done” state machine.
- **Plan quality depends on the model** and the planning prompt; there is no benchmark scoring in this release.
- **`--plan-first` is per user message**, not once per session.

&nbsp;
## Skills (Phase 4)

The agent can discover **reusable workflow packs** (Skills) from your repository. Skills keep long instructions out of the always-on prompt: at startup only **metadata** is listed; the full **body** is loaded on demand.

### Directory layout

Each Skill lives in its own folder under the workspace root:

```text
.mini-coding-agent/skills/<skill-name>/SKILL.md
```

Optional frontmatter (YAML) at the top of `SKILL.md`:

| Key | Required | Notes |
|-----|----------|-------|
| `name` | No | Defaults to the **directory name** if omitted |
| `description` | Recommended | Shown in the startup catalog; helps the model decide when to load |

Example:

```yaml
---
name: code-review
description: Review PRs against team standards. Use when the user mentions review, PR, or 审查.
---

# Code Review

1. Use `read_file` to inspect the change scope
2. Give graded feedback against acceptance criteria
```

Files in the Skill folder **besides** `SKILL.md` are **not** auto-loaded. Reference them in the body and let the agent `read_file` them when needed.

**Templates in this repo:**

- [`.mini-coding-agent/skills/README.md`](.mini-coding-agent/skills/README.md) — directory guide (Chinese)
- [`.mini-coding-agent/skills/SKILL.md.template`](.mini-coding-agent/skills/SKILL.md.template) — copy to start a new Skill
- [`.mini-coding-agent/skills/example-skill/SKILL.md`](.mini-coding-agent/skills/example-skill/SKILL.md) — runnable example (`--skills example-skill`)

If the skills directory is missing or empty, the agent starts normally with an empty catalog. A single broken Skill file is skipped with a stderr warning; other Skills still load.

### Two-stage loading

| Stage | What enters the prompt | When |
|-------|------------------------|------|
| **1 — Catalog** | `name` + `description` only | Agent startup / resume (`build_prefix`) |
| **2 — Body** | Full SKILL.md body (frontmatter stripped) | Model calls `load_skill`, or CLI `--skills` preloads at build time |

Stage 1 never includes Skill body text. Stage 2 writes into session memory (see below).

### `load_skill` vs `make_plan` vs `delegate`

- **`load_skill`** — loads a **reusable domain workflow** from a checked-in `SKILL.md` into session memory.
- **`make_plan`** — produces a **one-off task breakdown** (JSON steps) for the current user goal.
- **`delegate`** — runs a bounded **read-only sub-agent** to investigate (multi-step tools).

These are **parallel** capabilities; none replaces the others. File writes and shell commands still go through Phase 1 change governance and Phase 2 hooks.

### Tool: `load_skill`

| Item | Detail |
|------|--------|
| Risk | **Safe** — no approval prompt; does not write files or run shell |
| Parameters | `name` (required) — Skill name as shown in the startup catalog |
| Call format | `<tool>{"name":"load_skill","args":{"name":"code-review"}}</tool>` |

On success the tool returns a short confirmation and a `<skill_body>...</skill_body>` block. The body is also stored in session memory. Unknown names return a clear error string and **do not** update memory. Loading the same name again **overwrites** the stored body (re-reads from disk).

### Loaded skills in session memory

Successful loads are saved under:

```text
.mini-coding-agent/sessions/<session-id>.json  →  memory.loaded_skills
```

Each entry holds `name`, `description`, and `body`. Working memory (`memory_text()`) includes a summary and the loaded bodies in later prompts. In the REPL, run **`/memory`** to inspect the current task, plan summary (if any), **loaded skills**, tracked files, and notes.

**`/reset`** clears `loaded_skills` along with history, plan, and other memory fields.

Skills are **not** written to a separate file on disk beyond the session JSON.

### CLI: `--skills`

Comma-separated Skill names to **preload at agent startup** (stage 2 without waiting for the model):

```bash
uv run mini-coding-agent --skills example-skill "Explain how Skills work in this repo"
```

Multiple Skills:

```bash
uv run mini-coding-agent --skills code-review,example-skill --approval ask "Review README changes"
```

Works alongside **`--plan-first`** — for example, preload a workflow Skill and still require `make_plan` before risky tools in each turn.

Unknown names in `--skills` print a stderr warning; known names are still preloaded.

### Known limitations (Phase 4)

- **No hot reload.** The catalog is scanned at agent startup / resume; editing `SKILL.md` on disk is picked up on the next `load_skill` call (body is re-read from file), but the prefix catalog updates only after restart.
- **MVP frontmatter only.** Advanced fields (e.g. `allowed-tools`, dynamic shell injection) are not supported.
- **No REPL slash commands** such as `/code-review`; use `load_skill` or `--skills`.
- **No `.claude/skills` compatibility** — only `.mini-coding-agent/skills/`.
- **Child agents do not inherit** the parent session’s `loaded_skills`; each agent has its own memory.

&nbsp;
## Graph Harness (Phase 5)

Phase 5 adds an **optional orchestration shell** on top of the existing `ask()` loop. When `--harness off` (default), behavior is unchanged. When `--harness on`, each user message first runs a **Gate** (one short LLM call) to classify intent, then may run a **template DAG pipeline** instead of the free-form tool loop.

Governance (Phase 1), hooks (Phase 2), planning (Phase 3), and Skills (Phase 4) still apply inside pipeline nodes — file writes in the `generate` node go through the same `run_tool` → approval → checkpoint path.

### Five closed intents (Gate)

The Gate may output **only** these `intent_id` values (English ids; user messages may be Chinese or mixed):

| intent_id | Typical user intent | Pipeline (MVP) |
|-----------|---------------------|----------------|
| `generate_code` | New files, new features, add tests | locate → generate → verify → review |
| `fix_bug` | Tracebacks, test failures, wrong behavior | locate → generate → verify → review |
| `refactor` | Restructure without changing semantics | locate → **plan** → generate → verify → review |
| `explain` | Understand code only — **no edits** | locate → **explain** |
| `project_ops` | Run tests, pip, git status — **no source edits** | locate → **ops** → review |

Illegal Gate output or **`confidence=low`** → **open** fallback: the agent uses the normal `ask()` loop (same as `--harness off` for that turn).

Pipeline failure (node error, verify exhausted retries) also **falls back to open** with a short reason on stderr.

### CLI: `--harness` and `--gate-log`

| Flag | Default | Effect |
|------|---------|--------|
| `--harness off\|on` | `off` | `off`: every message uses `ask()` only (no Gate). `on`: Gate + pipeline when `confidence=high` and intent is one of the five above. |
| `--gate-log` | off | Print Gate classification to **stderr** (`[gate] intent_id=… confidence=… route=…`). Can be used with `--harness off` to **observe** Gate only (still runs one Gate LLM call per message). |

Examples:

```bash
# Normal REPL (unchanged)
uv run mini-coding-agent

# Observe Gate only; execution still uses ask()
uv run mini-coding-agent --gate-log "修 calc.py 的 bug"

# Full harness: Gate + template pipeline; low/illegal → ask()
uv run mini-coding-agent --harness on --approval auto "实现 hello.py"
```

Progress lines on stderr during a pipeline look like:

```text
[gate] intent_id=fix_bug confidence=high route=harness_pipeline skill=（无）
[harness] fix_bug 1/4 locate ok
[harness] fix_bug 2/4 generate ok
...
```

### Offline code graph: `rig build`

Before (or between) harness runs, build a local **RIG** (repository information graph) from Python sources:

```bash
uv run mini-coding-agent rig build --cwd .
# or: python mini_coding_agent.py rig build --cwd .
```

Output database:

```text
.mini-coding-agent/rig.db
```

The **`locate`** node queries RIG first (symbols, file paths, 1-hop neighbors), then falls back to `search` / traceback hints if the DB is missing. No cloud services; stdlib `ast` + SQLite only.

### Open fallback (when harness does not run the pipeline)

| Condition | Behavior |
|-----------|----------|
| `--harness off` and no `--gate-log` | Direct `ask()` — no Gate LLM |
| Gate `confidence=low` or invalid `intent_id` | `ask()` |
| Pipeline node failure or verify retries exhausted | stderr reason, then `ask()` |

`ask()` remains the **supported** entry for exploratory work and when the harness is unsure.

### Harness fields in session JSON

When Gate or pipeline runs, extra fields are stored under `.mini-coding-agent/sessions/<session-id>.json`:

| Field | Meaning |
|-------|---------|
| `last_gate` | Latest Gate result: `intent_id`, `confidence`, `route`, optional `skill` |
| `last_files_touched` | File paths touched in the last pipeline (from locate / generate) |
| `last_verify` | Last verify summary: `ok`, `method`, `summary` |
| `harness_last_node` | Observe-only: last completed node `{intent_id, node_id, type, ok}` |

**`/reset`** clears these harness fields along with history, `memory.plan`, and `memory.loaded_skills`.

Gate may optionally return a `skill` name; the pipeline preloads it via `load_skill` before execution.

### `--plan-first` vs Graph Harness

These features are **orthogonal but can conflict in practice**:

- **`--plan-first`** applies to the **`ask()`** loop: each user message must call `make_plan` successfully before the first risky tool in that turn.
- **`--harness on`** runs the **template pipeline** for high-confidence intents; risky work inside the pipeline uses `run_tool` on dedicated nodes (`generate`, `ops`), not the main ask tool loop.

**Recommendation:** do not combine `--plan-first` with `--harness on` for editing tasks until you understand both gates. If the pipeline’s `generate` node runs while `--plan-first` is set, `make_plan` may not have run in the current **ask** turn and risky tools can be blocked. Prefer **`--harness on` without `--plan-first`**, or use `--harness off --plan-first` for plan-gated open-loop work.

### MVP delivered vs future (5.7+)

| MVP (Phase 5.1–5.6) ✅ | Future (5.7+) |
|------------------------|---------------|
| LLM Gate, 5 closed intents | Rule-assisted / hybrid Gate |
| 5 static DAG templates + Planner | Sixth intent, domain sub-templates |
| Generic executor + 5 intent E2E tests | Benchmarks, template learning |
| RIG full rebuild (`rig build`) | Incremental RIG, Graphviz export |
| Locate: RIG + rg fallback | Vector / BM25 retrieval (needs deps) |
| Session: `last_gate`, `last_files_touched`, `last_verify` | Richer cross-turn planner injection |

### Known limitations (Phase 5 MVP)

- **Default `--harness off`.** You must opt in to the pipeline.
- **Gate adds one LLM call** per message when `--harness on` or `--gate-log` is set.
- **`explain` and `project_ops`** pipelines do not use change governance for file edits by design; `ops` only allows a fixed shell prefix allowlist.
- **No incremental RIG.** Re-run `rig build` after large refactors.
- **Tests use `FakeModelClient`.** Real Ollama Gate quality depends on the model.

&nbsp;
## Sessions and Resume

The agent saves sessions under the target workspace root in:

```text
.mini-coding-agent/sessions/
```

Resume the latest session:

```bash
uv run mini-coding-agent --resume latest
```


Resume a specific session:

```bash
uv run mini-coding-agent --resume 20260401-144025-2dd0aa
```


&nbsp;
## Interactive Commands

Inside the REPL, slash commands are handled directly by the agent instead of
being sent to the model as a normal task.

- `/help`
  shows the list of available interactive commands
- `/memory`
  prints the distilled session memory, including the current task, **plan summary** (if any), **loaded skills** (if any), tracked files, and notes
- `/session`
  prints the path to the current saved session JSON file
- `/reset`
  clears the current session history and distilled memory (including plan, loaded skills, and **harness fields**: `last_gate`, `last_files_touched`, `last_verify`, `harness_last_node`) but keeps you in the REPL
- `/exit`
  exits the interactive session
- `/quit`
  exits the interactive session; alias for `/exit`

&nbsp;
## Main CLI Flags

```bash
uv run mini-coding-agent --help
```

Without `uv`:

```bash
python mini_coding_agent.py --help
```

CLI flags are passed before the agent starts. Use them to choose the workspace,
model connection, resume behavior, approval mode, and generation limits.

Important flags:

- `--cwd`
  sets the workspace directory the agent should inspect and modify; default: `.`
- `--model`
  selects the Ollama model name, such as `qwen3.5:4b`; default: `qwen3.5:4b`
- `--host`
  points the agent at the Ollama server URL (usually not needed); default: `http://127.0.0.1:11434`
- `--ollama-timeout`
  controls how long the client waits for an Ollama response (usually not needed); default: `300` seconds
- `--resume`
  resumes a saved session by id or uses `latest`; default: start a new session
- `--approval`
  controls how risky tools are handled: `ask`, `auto`, or `never`; default: `ask`
- `--max-steps`
  limits how many model and tool turns are allowed for one user request; default: `6`
- `--max-new-tokens`
  caps the model output length for each step; default: `512`
- `--temperature`
  controls sampling randomness; default: `0.2`
- `--top-p`
  controls nucleus sampling for generation; default: `0.9`
- `--hooks-config`
  path to `hooks.yaml` for built-in hook toggles; default: `<workspace>/.mini-coding-agent/hooks.yaml`
- `--no-trace-display`
  disable per-tool stderr trace lines (overrides `hooks.yaml`)
- `--no-session-trace`
  disable session `tool_trace` JSON (overrides `hooks.yaml`)
- `--no-shell-audit`
  disable shell pattern audit hook (overrides `hooks.yaml`)
- `--plan-first`
  require a successful `make_plan` in each user request before the first risky tool (`write_file`, `patch_file`, `run_shell`); default: off
- `--skills`
  comma-separated Skill names to preload into session memory at startup (e.g. `code-review,example-skill`); default: none
- `--harness`
  Graph Harness: `off` (default, normal `ask()` only) or `on` (Gate + template pipeline for high-confidence intents; failures fall back to `ask()`)
- `--gate-log`
  print Gate intent classification to stderr each message; can be used with `--harness off` for observation only

**RIG subcommand** (not a flag on the main agent):

```bash
uv run mini-coding-agent rig build [--cwd .]
```

Builds `.mini-coding-agent/rig.db` for the `locate` pipeline node.

&nbsp;
## Example

See [EXAMPLE.md](EXAMPLE.md)

&nbsp;
## Notes & Tips

- The agent expects the model to emit either `<tool>...</tool>` or `<final>...</final>`.
- Different Ollama models will follow those instructions with different reliability.
- If the model does not follow the format well, use a stronger instruction-following model.
- The agent is intentionally small and optimized for readability, not robustness.
