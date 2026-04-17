# freecode

**A free, open-source terminal coding agent — Claude Code-style, powered by [z.ai](https://z.ai)'s free GLM APIs.**

`freecode` gives you an interactive AI pair-programmer in your terminal that can read and edit your code, run shell commands, and ship projects to GitHub and Vercel — all driven by a free LLM backend so it doesn't cost a cent to use.

> **Live site:** https://freecode.vercel.app · **Repo:** https://github.com/vasilysahrai/freecode

---

## Why this exists

Tools like Claude Code, Cursor, and Aider have reset the expectation for what a developer CLI should feel like. But most of them are paid or gated. `freecode` brings the same loop — natural-language requests, streamed reasoning, tool-calling, automated shipping — on top of a genuinely free model tier from z.ai so anyone can try agentic coding without paying.

---

## Features

- **Interactive REPL** with slash commands (`/help`, `/clear`, `/model`, `/cwd`).
- **Tool-using agent loop** with OpenAI-style function calling.
- **File tools** — `read_file`, `write_file`, `edit_file`, `list_dir`, `grep`.
- **Shell tool** — arbitrary commands with captured output and exit codes.
- **GitHub integration** — create a public repo and push your workspace in one call (via the `gh` CLI).
- **Vercel integration** — deploy the current directory in one call (via the `vercel` CLI).
- **One-shot mode** — `freecode -p "add a CI workflow"` for scripting.
- **Workspace sandboxing** — file tools refuse paths that escape the project root.
- **Rich terminal UI** — Claude Code-inspired panels, syntax highlighting, tool-call badges.

---

## Install

Requires Python ≥ 3.9.

```bash
pip install git+https://github.com/vasilysahrai/freecode.git
```

Or clone and install in editable mode:

```bash
git clone https://github.com/vasilysahrai/freecode.git
cd freecode
pip install -e .
```

---

## Configure

1. Grab a free API key at **[z.ai](https://z.ai)**.
2. Export it (or put it in a `.env` file in your project or `~/.freecode/.env`):

```bash
export ZAI_API_KEY=your_key_here
```

Optional env vars:

| Variable           | Default                              | Notes                             |
| ------------------ | ------------------------------------ | --------------------------------- |
| `FREECODE_MODEL`   | `glm-4.5-flash`                      | Any z.ai chat model id.           |
| `ZAI_BASE_URL`     | `https://api.z.ai/api/paas/v4`       | z.ai's OpenAI-compatible base.    |

For the GitHub and Vercel tools you'll also want the `gh` and `vercel` CLIs installed and authenticated.

---

## Use it

Start an interactive session in the directory you want the agent to work on:

```bash
cd path/to/project
freecode
```

Then just talk to it:

```
› read pyproject.toml and add a lint target to the dev dependencies
› write a pytest that covers the login route, run it, and fix anything red
› ship this to a new public GitHub repo called quickstart-bot, then deploy to Vercel
```

Or run a single prompt and exit:

```bash
freecode -p "summarise what this codebase does"
```

---

## How it works

```
┌──────────┐    messages     ┌──────────┐
│   you    │ ─────────────▶ │  freecode│
└──────────┘                 │  agent   │
      ▲                      │          │
      │   rendered output    │          │ ── tool_calls ──▶  [files] [bash] [grep] [gh] [vercel]
      │                      │          │ ◀── results ────
      │                      └────┬─────┘
      │                           │ chat
      │                           ▼
      │                    ┌─────────────┐
      └────────────────────│  z.ai GLM   │
                           └─────────────┘
```

Every turn the agent sends the conversation + a JSON schema for each tool to z.ai, receives either a natural-language reply or a set of tool calls, executes them locally, appends the results, and loops until the model is done.

---

## Project layout

```
freecode/
├── freecode/
│   ├── cli.py         # argparse + REPL
│   ├── agent.py       # tool-calling loop
│   ├── llm.py         # z.ai chat client
│   ├── config.py      # env/key loading
│   ├── ui.py          # rich terminal rendering
│   └── tools/         # read/write/edit/list/grep/bash/github/vercel
├── website/           # Vercel-deployed landing page
├── pyproject.toml
└── README.md
```

---

## Tech stack

- **Python 3.9+**
- **OpenAI Python SDK** — pointed at z.ai's OpenAI-compatible endpoint
- **Rich** — terminal rendering
- **prompt_toolkit** — input editing + history
- **z.ai GLM-4.5** — LLM backbone (free tier)
- **GitHub CLI** and **Vercel CLI** — shell-tool-powered integrations

---

## Skills demonstrated

Building this required:

- Designing an end-to-end **AI agent loop** with tool-calling, conversation state, and an extensible tool registry.
- Targeting an **OpenAI-compatible API** from a third-party provider (z.ai) and abstracting the client cleanly.
- Shipping a real, polished **Python CLI** — argparse, rich rendering, prompt_toolkit REPL, persistent history, slash commands.
- Writing **safe file operations** with workspace sandboxing and sensible size limits.
- Integrating with **real developer tooling** (`gh`, `vercel`, shell) from an LLM-driven control flow.
- Publishing an **open-source** project — MIT license, documentation, contributor-friendly structure, deployed docs site.

---

## Contributing

Issues and PRs welcome. If you add a tool, drop it in `freecode/tools/` and register it in `freecode/tools/registry.py`. Run `python -m compileall freecode` to sanity-check.

---

## License

[MIT](LICENSE) — do whatever you want.
