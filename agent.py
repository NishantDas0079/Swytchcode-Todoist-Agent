"""
Todoist Agent — powered by the OpenAI Agents SDK + Swytchcode.
 
The agent receives a natural-language instruction, decides which Todoist
action to take, and executes it by shelling out to the `swytchcode` CLI
(`swytchcode exec`). Swytchcode handles auth, retries, and schema
validation against Todoist's API; this script never talks to Todoist
directly.
 
Prerequisites (see README.md for full steps):
  - `swytchcode init` run in this project, with `swytchcode get todoist`
    and the relevant tools added via `swytchcode add <canonical_id>`.
  - OPENAI_API_KEY set in your environment.
  - Your Todoist auth token wired into swytchcode per its docs (check
    `swytchcode info <canonical_id>` for exactly what the tool expects —
    usually an Authorization header or token input).
 
IMPORTANT: The canonical IDs below (CREATE_TASK_TOOL, LIST_TASKS_TOOL)
are placeholders. Run:
    swytchcode list methods todoist
after `swytchcode get todoist`, and replace these with the real
canonical IDs shown in that output before running this script.
"""
 
import json
import shutil
import subprocess
import sys
 
from agents import Agent, Runner
from agents.decorators import tool
 
# Confirmed via `swytchcode info <id>` against Todoist.todoist@3.1.0
CREATE_TASK_TOOL = "todoist.api.tasks.create.1"  # NOT .create (no suffix) — that one is actually "Update Task"
LIST_TASKS_TOOL = "todoist.api.tasks.list"
 
 
import os
 
from dotenv import load_dotenv
 
load_dotenv()  # reads .env in this folder and sets os.environ from it

SWYTCHCODE = shutil.which("swytchcode.cmd") or shutil.which("swytchcode")
if not SWYTCHCODE:
    raise RuntimeError(
        "swytchcode CLI not found on PATH. Install it with: npm install -g swytchcode"
    )

TODOIST_TOKEN = os.environ.get("TODOIST_API_TOKEN")
if not TODOIST_TOKEN:
    raise RuntimeError(
        "Set the TODOIST_API_TOKEN environment variable before running this agent "
        "(from Todoist \u2192 Settings \u2192 Integrations \u2192 Developer)."
    )
 
 
def _run_swytchcode(canonical_id: str, args: dict) -> dict:
    """Run `swytchcode exec` via its full JSON-stdin mode: {"tool": ..., "args": ...}.
 
    Uses subprocess.run (not os.system / shell=True) so stdin/stdout are
    handled as text streams cleanly and large responses aren't truncated.
    Always injects the Authorization header, confirmed working via
    `swytchcode exec ... --dry-run --json --input Authorization="Bearer <token>"`.
    """
    args = {**args, "Authorization": f"Bearer {TODOIST_TOKEN}"}
    payload = {"tool": canonical_id, "args": args}
 
    result = subprocess.run(
        [SWYTCHCODE, "exec", "--json"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
 
    if result.returncode != 0:
        raise RuntimeError(
            f"swytchcode exec failed (exit {result.returncode}): {result.stderr.strip()}"
        )
 
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"swytchcode returned non-JSON output: {result.stdout!r}")
 
    if output.get("status_code", 200) >= 400:
        raise RuntimeError(
            f"Todoist API error {output['status_code']}: {json.dumps(output.get('data'))}"
        )
 
    return output.get("data", output)
 
 
@tool
def add_todoist_task(content: str, due_string: str | None = None, priority: int | None = None) -> str:
    """Create a new task in the user's Todoist.
 
    Args:
        content: The task text, e.g. "Review the pull request".
        due_string: Optional natural-language due date, e.g. "tomorrow", "Friday", "next Monday".
        priority: Optional priority from 1 (normal) to 4 (urgent).
    """
    body = {"content": content}
    if due_string:
        body["due_string"] = due_string
    if priority:
        body["priority"] = priority
 
    data = _run_swytchcode(CREATE_TASK_TOOL, {"body": body})
    task_id = data.get("id", "unknown")
    return f"Created Todoist task (id={task_id}): {content!r}" + (
        f", due {due_string}" if due_string else ""
    )
 
 
@tool
def list_todoist_tasks(label: str | None = None, project_id: str | None = None) -> str:
    """List the user's active Todoist tasks, optionally narrowed down.
 
    Args:
        label: Optional label name to filter by, e.g. "work".
        project_id: Optional project ID to filter by.
    """
    params = {}
    if label:
        params["label"] = label
    if project_id:
        params["project_id"] = project_id
 
    data = _run_swytchcode(LIST_TASKS_TOOL, {"params": params})
    tasks = data.get("results", [])
 
    if not tasks:
        return "No tasks found."
 
    lines = [f"- {t.get('content', '(no content)')}" for t in tasks]
    return "Current tasks:\n" + "\n".join(lines)
 
 
agent = Agent(
    name="Todoist Assistant",
    instructions=(
        "You are a helpful assistant that manages the user's Todoist tasks. "
        "Use add_todoist_task to create tasks and list_todoist_tasks to check "
        "existing ones. Confirm what you did in plain language after each action."
    ),
    tools=[add_todoist_task, list_todoist_tasks],
)
 
 
def main():
    if len(sys.argv) < 2:
        print('Usage: python agent.py "your instruction here"')
        sys.exit(1)
 
    user_prompt = " ".join(sys.argv[1:])
    result = Runner.run_sync(agent, user_prompt)
    print(result.final_output)
 
 
if __name__ == "__main__":
    main()