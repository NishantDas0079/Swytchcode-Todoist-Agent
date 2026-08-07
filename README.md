# Todoist Agent

A single-API AI agent that manages your Todoist tasks through natural language,
built with the **OpenAI Agents SDK** and **Swytchcode**.

## How it works

1. You give the agent a plain-English instruction (e.g. *"add a task to review the PR by tomorrow"*).
2. The OpenAI Agents SDK decides which tool to call — `add_todoist_task` or `list_todoist_tasks`.
3. That tool shells out to `swytchcode exec`, which handles authentication,
   retries, and schema validation against Todoist's real API.
4. The result comes back through Swytchcode → the tool → the agent, which
   reports what it did in plain language.

No direct HTTP calls to Todoist happen in this codebase — Swytchcode is the
only thing that talks to Todoist.

## Setup

### 1. Install the Swytchcode CLI and set up this project

```bash
npm install -g swytchcode   # or: curl -fsSL https://cli.swytchcode.com/install.sh | sh
swytchcode login
swytchcode init --editor none --mode production
swytchcode get todoist
```

### 2. Find the real canonical IDs

```bash
swytchcode list methods todoist
```

Open `agent.py` and replace the placeholder values of `CREATE_TASK_TOOL` and
`LIST_TASKS_TOOL` with whatever canonical IDs that command actually prints.

### 3. Enable those tools

```bash
swytchcode add <create_task_canonical_id>
swytchcode add <list_tasks_canonical_id>
```

### 4. Wire up your Todoist auth

Check what the tool expects:

```bash
swytchcode info <create_task_canonical_id>
```

Get a Todoist API token from Todoist → Settings → Integrations → Developer,
and provide it however the `info` output indicates (commonly an
`Authorization` header or token input passed at exec time).

Sanity check before running the agent for real:

```bash
swytchcode exec <create_task_canonical_id> --dry-run --json
```

### 5. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install openai-agents
export OPENAI_API_KEY=sk-...   # Windows: setx OPENAI_API_KEY "sk-..."
```

## Usage

```bash
python agent.py "add a task to review the pull request by tomorrow"
python agent.py "what's on my todo list today?"
```

## Project structure

```
todoist-agent/
├── agent.py       # Agent definition and tools
├── README.md
├── requirements.txt
└── .gitignore
```

## Notes

- Never commit your `OPENAI_API_KEY` or Todoist token. Use environment
  variables or a gitignored `.env` file.
- This agent uses Swytchcode's `production` mode by default (set during
  `swytchcode init`). Switch to `sandbox` mode if Todoist's integration
  supports it and you want to test without touching your real task list.
