# Taskwarrior Flow (TWF)

Taskwarrior Flow (TWF) enhances your [Taskwarrior](https://taskwarrior.org) workflow with a CLI that adds task templates, saved queries, multiple task databases, natural date parsing, and AI-powered natural language task creation.

## Installation

### Standard (no AI)

```shell
# pipx (recommended for CLI tools)
pipx install taskwarrior_flow

# uv
uv tool install taskwarrior_flow
```

### With AI support

AI features require the `ai` extra, which bundles the Anthropic and OpenAI SDKs.

```shell
# pipx
pipx install "taskwarrior_flow[ai]"

# uv
uv tool install "taskwarrior_flow[ai]"
```

To add only one provider:

```shell
uv tool install taskwarrior_flow
uv add anthropic   # or: uv add openai
```

## Configuration

TWF reads its configuration from `~/.local/share/tw_flow/config.json` by default. The file is created automatically on first run.

```json
{
  "flow_config": {
    "personal": {"data": "~/.task", "config": "~/.taskrc"}
  },
  "ai": {
    "provider": "anthropic",
    "anthropic_api_key": "sk-ant-...",
    "openai_api_key":    "sk-..."
  },
  "add_templates": { ... },
  "saved_queries":  { ... }
}
```

> **Note:** Avoid committing the config file to version control if it contains API keys. Environment variables are the safer option for CI or shared machines.

### Using with m_taskwarrior_d.nvim

If you use the [m_taskwarrior_d.nvim](https://github.com/huantrinh1802/m_taskwarrior_d.nvim) Neovim plugin, it manages its own config file. Point TWF at it by exporting `TW_CONFIG` in your shell profile (`~/.bashrc`, `~/.zshrc`, `~/.config/fish/config.fish`, etc.):

```shell
# bash / zsh
export TW_CONFIG="$HOME/.local/share/nvim/m_taskwarrior_d.json"

# fish
set -x TW_CONFIG "$HOME/.local/share/nvim/m_taskwarrior_d.json"
```

This lets both tools share the same groups, templates, and queries.

### AI key resolution order

For the provider, TWF checks (first match wins):

1. `--provider` CLI flag
2. `TW_AI_PROVIDER` environment variable
3. `ai.provider` in TW_CONFIG
4. Default: `anthropic`

For the API key, TWF checks:

1. `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` environment variable
2. `ai.anthropic_api_key` / `ai.openai_api_key` in TW_CONFIG

## Features

### Multiple task groups

Route commands to different Taskwarrior databases by group name:

```shell
twf task add "Personal errand" due:tomorrow
twf work add "Write quarterly report" project:reports priority:H
```

Groups are defined under `flow_config` in TW_CONFIG.

### Natural date parsing

Use `@...@` to write dates in plain English anywhere in a command:

```shell
twf task add "Team sync" due:@next Monday at 10am@
twf work mod 3 wait:@in two weeks@
```

### Task templates

Create reusable task blueprints with typed fields (text, list, date, annotation):

```shell
twf utils add template   # define a new template
twf utils add task       # create a task from a saved template
twf utils view template  # inspect a template's fields
twf utils edit template  # modify an existing template
```

### Saved queries

Save and rerun complex Taskwarrior filter expressions:

```shell
twf utils add query      # save a new query
twf utils view task      # run a saved query
twf utils edit query     # update a saved query
```

### AI natural language input

Convert a plain-English description into a Taskwarrior command, preview it, then confirm:

```shell
twf ai "buy groceries by tomorrow, high priority"
# → add "buy groceries" due:tomorrow priority:H

twf ai "team meeting every Monday" --group work
# → add "team meeting" recur:weekly due:monday

twf ai "call John next Friday" --provider openai
# → add "call John" due:friday
```

**Options:**

| Flag | Short | Description |
|------|-------|-------------|
| `--group` | `-g` | Task group to add the task to (default: first group in config) |
| `--provider` | `-p` | AI provider: `anthropic` or `openai` |

## Development

```shell
# Clone and set up
git clone https://github.com/huantrinh1802/taskwarrior_flow
cd taskwarrior_flow

# Install with dev dependencies (uv)
uv sync --group dev

# Install with AI extras
uv sync --group dev --extra ai

# Run tests
uv run pytest

# Lint
uv run ruff check tools/
```

## Related tools

- [Taskwarrior](https://taskwarrior.org) — the task manager this tool wraps
- [m_taskwarrior_d.nvim](https://github.com/huantrinh1802/m_taskwarrior_d.nvim) — Neovim plugin that shares the same TW_CONFIG format
